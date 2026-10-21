import hashlib
import sqlite3

import jwt
from flask import Flask, request

app = Flask(__name__)
app.config["SESSION_COOKIE_SECURE"] = False


@app.route("/login", methods=["POST"])
def login():
    pw = hashlib.md5(request.form["password"].encode()).hexdigest()  # V3: weak hash
    token = jwt.encode({"user": request.form["user"]}, "key", algorithm="HS256")  # V3: no exp
    return token


@app.route("/users/<user_id>/orders")
def orders(user_id):  # V1: no check that user_id is the logged-in user
    db = sqlite3.connect("shop.db")
    name = request.args.get("name")
    db.execute("SELECT * FROM orders WHERE user_id = " + user_id + " AND name = '" + name + "'")  # V2
    return "ok"
