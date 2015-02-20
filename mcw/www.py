from flask import Flask, session, request
from flask.ext.socketio import SocketIO

from mcw.signals import (
    on_starting, on_started, on_stopping, on_stopped,
    on_stdin_message, on_stdout_message, on_stderr_message
)


class MinecraftAppMiddleware(object):
    def __init__(self, minecraft, app, socketio, namespace='/main'):
        self.minecraft = minecraft
        self.app = app
        self.socketio = socketio
        self.namespace = namespace

        socketio._on_message('connect', self.on_connect, namespace=namespace)
        socketio._on_message('command', self.on_command, namespace=namespace)
        socketio._on_message(
            'server-start', self.on_server_start, namespace=namespace
        )
        socketio._on_message(
            'server-stop', self.on_server_stop, namespace=namespace
        )
        socketio._on_message(
            'server-restart', self.on_server_restart, namespace=namespace
        )

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

    def on_server_restart(self, message):
        if not self.minecraft.is_running:
            return

        def restart(minecraft):
            print '----------------------------------------->'
            if not minecraft.is_running:
                minecraft.start()
            on_stopped.disconnect(restart, sender=minecraft)
        on_stopped.connect(restart, sender=self.minecraft)

        self.minecraft.stop()

    def send_server_state(self):
        self.socketio.emit('server-state',  {
            'server_state': self.minecraft.state
        }, namespace=self.namespace)

    def on_state_change(self, minecraft):
        self.send_server_state()

    def on_stdout(self, minecraft, message):
        self.socketio.emit('console-message', {
            'message': message, 'type': 'stdout'
        }, namespace=self.namespace)

    def on_stderr(self, minecraft, message):
        self.socketio.emit('console-message', {
            'message': message, 'type': 'stderr'
        }, namespace=self.namespace)


def create_intstance(secret_key):
    app = Flask(__name__)
    app.secret_key = secret_key

    from mcw.views.index import index
    app.register_blueprint(index)

    socketio = SocketIO()
    socketio.init_app(app)

    return (app, socketio)

