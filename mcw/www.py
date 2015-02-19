from flask import Flask



def create_intstance(secret_key):
    app = Flask(__name__)
    app.secret_key = secret_key

    from mcw.views.index import index, socketio

    app.register_blueprint(index)

    socketio.init_app(app)

    return (app, socketio)

