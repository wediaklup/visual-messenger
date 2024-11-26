from functools import wraps
from hashlib import sha256
from datetime import datetime
import typing as t

from flask import Flask, render_template, abort, jsonify, make_response, request, redirect
from flask_socketio import SocketIO
import psql
from dbconnect import Adapter

import customloginlib


app = Flask(__name__)
socketio = SocketIO(app)

SERVERNAME = "hector"
SCHEMA = "visual_messenger"


class CommonSQLObject(psql.SQLObject):
    SERVER_NAME = SERVERNAME
    SCHEMA_NAME = SCHEMA


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_user()
        if not user:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("/login.html", error="")
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        res = customloginlib.login(username, password)

        if res.valid:
            print(res.data)
            response = make_response(redirect("/"))
            response.set_cookie("validator", res.data)
            return response

        return render_template("login.html", error="invalid username/password"), 401


@app.route("/")
@login_required
def root():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("/register.html")
    elif request.method ==  "POST":
        username = request.form["username"]
        password = request.form["password"]
        password_check = request.form["password_check"]

        if password != password_check:
            return render_template("/register.html", error="password and password_check do not match"), 400

        customloginlib.login(username, password, True)
        return redirect("/login")

@login_required
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "GET":
        return render_template("/settings.html")

@login_required
@app.route("/settings/change_img", methods=["POST"])
def change_img():
    for key, value in request.files.items():
        tone_indicator = key.split("_")[1]
        mime_type = value.mimetype
        buffer = value.stream
        customloginlib.get_user().upload_img(tone_indicator, buffer, mime_type)
    
    return redirect("/settings")

@login_required
@app.route("/settings/change_password", methods=["POST"])
def settings():
    if request.method == "POST":
        if request.form["password"] != request.form["check_password"]:
            return render_template("/settings", errormsg="Password doesn't match Check")
        
        user = customloginlib.User.get(get_user().id)
        salt = user.salt
        password = request.form["password"]
        user.sha256 = customloginlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=4096, r=32, p=2).hex()
        user.commit()
        return redirect("/settings")

def get_user() -> t.Union[customloginlib.User, None]:
    """USE AS IN:
    ```
    user = get_user()
    if user is None:
        return redirect_login()
    ```
    """
    user = customloginlib.get_login(request.cookies.get("validator"))
    if user is None:
        return None
    return user


if __name__ == "__main__":
    socketio.run(debug=True, host="0.0.0.0", port=9980)

