from flask import Flask, request, make_response
import sqlite3
from hashlib import sha256
import uuid

app = Flask(__name__)


@app.route("/")
@app.route("/home")
def index():
    return {"message": "Hello World!"}


@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return "event-scheduling-api is up!", 200


"""connect = sqlite3.connect("database.db")
connect.execute("DROP TABLE USERS")"""
connect = sqlite3.connect("database.db")
connect.execute("CREATE TABLE IF NOT EXISTS USERS (userId TEXT, name TEXT, surname TEXT, email TEXT, password TEXT)")


@app.route("/createUser", methods=["POST"])
def create_user():
    if request.is_json:
        payload = dict(request.get_json())
        user_id = str(uuid.uuid4())
        name = payload.get("name")
        surname = payload.get("surname")
        email = payload.get("email")
        password = sha256(str(payload.get("password")).encode("utf-8")).hexdigest()
        with sqlite3.connect("database.db") as users:
            cursor = users.cursor()
            cursor.execute(
                "INSERT INTO USERS (userId, name, surname, email, password) VALUES (?, ?, ?, ?, ?)",
                (user_id, name, surname, email, password)
            )
            users.commit()
        return "OK", 200
    else:
        return "Request body must be json!", 500


@app.route("/users", methods=["GET"])
def get_users():
    connect = sqlite3.connect("database.db")
    cursor = connect.cursor()
    cursor.execute("SELECT name, surname, email FROM USERS")

    data = cursor.fetchall()
    return str(data), 200


@app.route("/login", methods=["POST"])
def login():
    if request.is_json:
        payload = dict(request.get_json())
        email = payload.get("email")
        password_from_user = sha256(str(payload.get("password")).encode("utf-8")).hexdigest()

        connect = sqlite3.connect("database.db")
        cursor = connect.cursor()
        cursor.execute("SELECT userId, password FROM USERS WHERE email = ?", (email,))
        data = cursor.fetchall()
        password_from_db = data[0][1]
        user_id = data[0][0]

        if password_from_user == password_from_db:
            resp = make_response()
            resp.set_cookie("session_id", user_id)
            return resp, 200
        else:
            return "Unauthorized", 401
    else:
        return "Request body must be json!", 500


if __name__ == "__main__":
    app.run(debug=False, port=10000)
