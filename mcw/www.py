from flask import Flask, session, request, g
from flask.ext.socketio import SocketIO

from mcw.signals import (
    on_backup_started, on_backup_stopped, on_backup_deleted,
    on_starting, on_started, on_stopping, on_stopped,
    on_stdin_message, on_stdout_message, on_stderr_message
)
from mcw.utils import pretty

import time
import gevent


class MinecraftAppMiddleware(object):
    def __init__(self, minecraft, backup, app, socketio, namespace='/main'):
        self.minecraft = minecraft
        self.backup = backup
        self.app = app
        self.socketio = socketio
        self.namespace = namespace

        self._info = (self.minecraft.info, time.time())

        socketio._on_message('connect', self.on_connect, namespace=namespace)
        socketio._on_message('command', self.on_command, namespace=namespace)
        socketio._on_message(
            'server-start', self.on_server_start, namespace=namespace
        )
        socketio._on_message(
            'server-stop', self.on_server_stop, namespace=namespace
        )
        socketio._on_message(
            'request-server-info', self.on_request_si, namespace=namespace
        )
        socketio._on_message(
            'backup-new', self.on_backup_new, namespace=namespace
        )
        socketio._on_message(
            'backup-delete', self.on_backup_delete, namespace=namespace
        )

        on_backup_started.connect(self.on_backup_started, sender=self.backup)
        on_backup_stopped.connect(self.on_backup_stopped, sender=self.backup)
        on_backup_deleted.connect(self.on_backup_deleted, sender=self.backup)
        on_starting.connect(self.on_state_change, sender=self.minecraft)
        on_started.connect(self.on_state_change, sender=self.minecraft)
        on_stopping.connect(self.on_state_change, sender=self.minecraft)
        on_stopped.connect(self.on_state_change, sender=self.minecraft)
        on_stdout_message.connect(self.on_stdout, sender=self.minecraft)
        on_stderr_message.connect(self.on_stderr, sender=self.minecraft)

    def on_connect(self):
        if not session.get('loggedin', False):
            return request.namespace.disconnect()

        self.socketio.emit('welcome',  {}, namespace=self.namespace)
        self.send_server_state()
        self.send_server_info()

    def on_command(self, message):
        command = message.get('command')
        if command:
            self.minecraft._write('{}\n'.format(command.strip()))

    def on_server_start(self, message):
        if self.minecraft.is_running:
            return

        self.minecraft.start()

    def on_server_stop(self, message):
        if not self.minecraft.is_running:
            return

        self.minecraft.stop()

    def send_server_info(self):
        if self._info[1] + 15 < time.time() or self._info[0] is None:
            self._info = (self.minecraft.info, time.time())

        cpu = 0
        memory = 0
        if self.minecraft.process is not None:
            cpu = self.minecraft.process.cpu_percent()
            memory = self.minecraft.process.memory_info()[0]

        self.socketio.emit('server-info', {
            'info': self._info[0],
            'cpu': cpu, 'memory': memory
        }, namespace=self.namespace)

    def on_request_si(self, message):
        self.send_server_info()

    def send_server_state(self):
        start_time = None
        if self.minecraft.process is not None:
            start_time = self.minecraft.process.create_time()

        self.socketio.emit('server-state',  {
            'state': self.minecraft.state,
            'start_time': start_time
        }, namespace=self.namespace)

    def on_backup_new(self, message):
        label = message.get('label') or 'Unlabeled'
        self.backup.create_user_backup(label.strip())

    def on_backup_delete(self, message):
        try:
            self.backup.delete_backup(message['name'])
        except (KeyError, ValueError):
            pass

    def on_backup_deleted(self, backup, name):
        self.socketio.emit('backup-deleted', {
            'name': name
        }, namespace=self.namespace)

    def on_backup_started(self, backup, type, name, label):
        self.socketio.emit('backup-started', {
            'type': type, 'name': name, 'label': label
        }, namespace=self.namespace)

    def on_backup_stopped(self, backup, type, name, label, date, size):
        self.socketio.emit('backup-stopped', {
            'type': type, 'name': name, 'label': label,
            'datestr': date.strftime('%c'),
            'time': time.mktime(date.timetuple()),
            'size': size
        }, namespace=self.namespace)

    def on_state_change(self, minecraft):
        self.send_server_state()
        self.send_server_info()

    def on_stdout(self, minecraft, message):
        self.socketio.emit('console-message', {
            'message': message, 'type': 'stdout'
        }, namespace=self.namespace)

    def on_stderr(self, minecraft, message):
        self.socketio.emit('console-message', {
            'message': message, 'type': 'stderr'
        }, namespace=self.namespace)


def create_intstance(minecraft, backup, secret_key):
    app = Flask(__name__)
    app.secret_key = secret_key

    from mcw.views.index import index
    app.register_blueprint(index)

    def before_request():
        g.minecraft = minecraft
        g.backup = backup
    app.before_request(before_request)

    app.jinja_env.filters['sizeof_fmt'] = pretty.sizeof_fmt
    app.jinja_env.filters['mktime'] = lambda d: time.mktime(d.timetuple())

    socketio = SocketIO()
    socketio.init_app(app)

    mw = MinecraftAppMiddleware(minecraft, backup, app, socketio)

    return (app, socketio, mw)

