from flask import request, session
from flask.ext.socketio import SocketIO, emit


socketio = SocketIO()

NAMESPACE = '/main'

@socketio.on('connect', namespace=NAMESPACE)
def on_connect():
    if not session.get('loggedin', False):
        return request.namespace.disconnect()
    emit('welcome', {})


