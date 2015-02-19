from mcw.www import create_intstance

from flask import g

app = create_intstance()
app.config.password = 'yolo'
app.secret_key = 'ajskdfhuw8495u89wusfdiof'
app.run(debug=True)
