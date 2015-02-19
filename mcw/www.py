from flask import Flask


def create_intstance():
    app = Flask(__name__)

    from mcw.views.index import index

    app.register_blueprint(index)

    return app
