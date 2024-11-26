from functools import wraps
from hashlib import sha256
from datetime import datetime
import typing as t

from flask import Flask, render_template, abort, jsonify, make_response, request, redirect
from flask_socketio import SocketIO, emit, join_room, leave_room, send
import psql
from dbconnect import Adapter

import customloginlib
from sqladapter import Message, Room


app = Flask(__name__)
socketio = SocketIO(app)


PROTOCOL_VERSION = 0

MESSAGE_VERSION = "version"
MESSAGE_HEADER = "header"
MESSAGE_BODY = "body"


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
    user = get_user()
    return render_template("index.html", available=user.get_available_channels())


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
def change_password():
    if request.method == "POST":
        if request.form["password"] != request.form["check_password"]:
            return render_template("/settings", errormsg="Password doesn't match Check")

        user = customloginlib.User.get(get_user().id)
        salt = user.salt
        password = request.form["password"]
        user.sha256 = customloginlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=4096, r=32, p=2).hex()
        user.commit()
        return redirect("/settings")


@login_required
@app.route("/create-channel", methods=["GET", "POST"])
def create_channel():
    user = get_user()

    if request.method == "POST":
        form = request.form
        files = request.files

        music = files["music"]
        image = files["image"]

        rid = Room.get_increment()
        obj = Room(rid, form["name"], ..., user.id, music.stream.read(), music.mimetype, image.stream.read(), image.mimetype)
        obj.commit()

        Room._db().query("INSERT INTO room_link (roomid, userid) VALUES (%s, %s)", (rid, user.id))

        for user in form["allowed-users"].split(","):
            username = user.strip()
            user_obj = customloginlib.User.get(name=username)
            Room._db().query("INSERT INTO room_link (roomid, userid) VALUES (%s, %s)", (rid, user_obj.id))

        return redirect(f"/?room={rid}")

    return render_template("create-channel.html")


@socketio.on("connect")
def on_connect(auth):
    username = auth[MESSAGE_HEADER]["username"]
    password = auth[MESSAGE_HEADER]["password"]

    response = customloginlib.login(username, password)

    if not response.valid:
        emit("disconnect", {
            MESSAGE_VERSION: PROTOCOL_VERSION,
            MESSAGE_HEADER: {"code": 401, "origin": "bouncer"},
            MESSAGE_BODY: "Credentials do not match database."
        })
        return

    req_room = int(auth[MESSAGE_HEADER]["req-room"])
    room = Room.get(req_room)


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
    socketio.run(app, debug=True, host="0.0.0.0", port=9980)

