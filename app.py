from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, World!"

# Make sure to expose the app as a WSGI callable
application = app
