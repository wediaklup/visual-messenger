from flask import Flask, render_template, abort, jsonify, make_response


app = Flask(__name__)



@app.route("/")
def root():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=9980)

