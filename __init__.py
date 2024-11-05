from flask import Flask, render_template, abort, jsonify, make_response, request, redirect
from functools import wraps
from hashlib import sha256
from datetime import datetime
import psql
from dbconnect import Adapter

app = Flask(__name__)

SERVERNAME = "hector"
SCHEMA = "visual_messenger"

class CommonSQLObject(psql.SQLObject):
    SERVER_NAME = SERVERNAME
    SCHEMA_NAME = SCHEMA

class User(CommonSQLObject):
    TABLE_NAME = "users"
    SQL_KEYS = ["id", "name", "sha256", "validator", "validation_time", "admin"]
    PRIMARY_KEY = "id"

    def __init__(self, id:int, name:str, sha256:str, validator:str, validation_time:datetime, admin:bool):
        super().__init__()
        self.id = id
        self.name = name
        self.sha256 = sha256
        self.validator = validator
        self.validation_time = validation_time
        self.admin = admin

    @staticmethod
    def construct(response):
        return [User(x[0], x[1], x[2], x[3], x[4], x[5]) for x in response]


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("/login.html", error="")
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["passsword"]

        try:
            users = User.get(name=username, sha256=sha256(password.encode("utf-8")).hexdigest())
        except KeyError:
            return render_template("login.html", error="invalid username/password")
        
        return redirect("/")

@app.route("/")
#@login_required
def root():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=9980)

