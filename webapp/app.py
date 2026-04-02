"""
GeoStructPy Web Application
Lightweight Flask app for geotechnical engineering calculations.
Intended for APEC Consultancy team use.
"""

from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/mononobe-okabe")
def mononobe_okabe():
    return render_template("mononobe_okabe.html")


@app.route("/terzaghi")
def terzaghi():
    return render_template("terzaghi.html")


@app.route("/meyerhof")
def meyerhof():
    return render_template("meyerhof.html")


@app.route("/stability")
def stability():
    return render_template("stability.html")


@app.route("/micropile")
def micropile():
    return render_template("micropile.html")


@app.route("/changelog")
def changelog():
    return render_template("changelog.html")


@app.route("/theory")
def theory():
    return render_template("theory.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
