from mcw.www import create_intstance

from flask import g

app, socketio = create_intstance('ajskdfhuw8495u89wusfdiof')
app.config.password = 'yolo'
socketio.run(app, use_reloader=True)
