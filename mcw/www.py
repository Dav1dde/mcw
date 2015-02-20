from flask import Flask, session, request
from flask.ext.socketio import SocketIO

from mcw.signals import (
    on_started, on_stopped,
    on_stdin_message, on_stdout_message, on_stderr_message
)

from collections import namedtuple


class MinecraftAppMiddleware(object):
    def __init__(self, minecraft, app, socketio, namespace='/main'):
        self.minecraft = minecraft
        self.app = app
        self.socketio = socketio
        self.namespace = namespace

        socketio._on_message('connect', self.on_connect, namespace=namespace)
        socketio._on_message('command', self.on_command, namespace=namespace)

        on_started.connect(self.on_started, sender=self.minecraft)
        on_stopped.connect(self.on_stopped, sender=self.minecraft)
        on_stdout_message.connect(self.on_stdout, sender=self.minecraft)
        on_stderr_message.connect(self.on_stderr, sender=self.minecraft)

    def on_connect(self):
        if not session.get('loggedin', False):
            return request.namespace.disconnect()

        state = 'running' if self.minecraft.is_running else 'stopped'

        self.socketio.emit('welcome',  {
            'server_state': state
        }, namespace=self.namespace)

    def on_command(self, message):
        command = message.get('command')
        if command:
            self.minecraft._write('{}\n'.format(command.strip()))

    def on_started(self, minecraft):
        self.socketio.emit('server-state',  {
            'server_state': 'running'
        }, namespace=self.namespace)

    def on_stopped(self, minecraft):
        self.socketio.emit('server-state',  {
            'server_state': 'stopped'
        }, namespace=self.namespace)

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

