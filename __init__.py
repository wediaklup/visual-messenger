from flask import Flask, render_template, abort, jsonify, make_response, session, redirect
from functools import wraps
from sqlite3 import connect
from hashlib import sha256

app = Flask(__name__)
con = connect("tables.sql")
cur = con.cursor()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login")
def login():
    return render_template("/login.html")

@app.route("/")
#@login_required
def root():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=9980)

