from sys import platform
if platform == "win32":
    from waitress import serve
from api import app

if platform == "win32":
    serve(app, listen='0.0.0.0:8080')
