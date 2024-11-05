from functools import wraps
from hashlib import sha256
from datetime import datetime
import typing as t

from flask import Flask, render_template, abort, jsonify, make_response, request, redirect
import psql
from dbconnect import Adapter

import customloginlib


app = Flask(__name__)

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
        return f
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
            response = make_response(redirect("/"))
            response.set_cookie("validator", res.data)
            return response, 200

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
            render_template("/register.html", error="password and password_check do not match")

        customloginlib.login("username", "password", True)


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
    app.run(debug=True, host="0.0.0.0", port=9980)

