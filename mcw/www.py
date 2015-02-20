from flask import Flask

from mcw.minecraft import (
    on_stdin_message, on_stdout_message, on_stderr_message
)
from mcw.views.socket import NAMESPACE

from collections import namedtuple


class MinecraftAppMiddleware(object):
    def __init__(self, minecraft, app, socketio):
        self.minecraft = minecraft
        self.app = app
        self.socketio = socketio

        on_stdout_message.connect(self.on_stdout, sender=self.minecraft)
        on_stderr_message.connect(self.on_stderr, sender=self.minecraft)

    def on_stdout(self, minecraft, message):
        self.socketio.emit('console-message', {
            'message': message, 'type': 'stdout'
        }, namespace=NAMESPACE)

    def on_stderr(self, minecraft, message):
        self.socketio.emit('console-message', {
            'message': message, 'type': 'stderr'
        }, namespace=NAMESPACE)


def create_intstance(secret_key):
    app = Flask(__name__)
    app.secret_key = secret_key

    from mcw.views.index import index
    from mcw.views.socket import socketio

    app.register_blueprint(index)

    socketio.init_app(app)

    return (app, socketio)

