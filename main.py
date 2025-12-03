from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
import sqlite3
from hashlib import sha256
import uuid
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)


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
connect.execute("""CREATE TABLE IF NOT EXISTS EVENTS (
    eventId TEXT PRIMARY KEY,
    title TEXT,
    type TEXT,
    selectedDates TEXT,
    selectedDays TEXT,
    startTime TEXT,
    endTime TEXT,
    timezone TEXT,
    createdAt TEXT
)""")
connect.execute("""CREATE TABLE IF NOT EXISTS PARTICIPANTS (
    participantId TEXT PRIMARY KEY,
    eventId TEXT,
    name TEXT,
    joinedAt TEXT,
    FOREIGN KEY (eventId) REFERENCES EVENTS(eventId)
)""")
connect.execute("""CREATE TABLE IF NOT EXISTS VOTES (
    voteId TEXT PRIMARY KEY,
    eventId TEXT,
    participantId TEXT,
    timeSlot TEXT,
    FOREIGN KEY (eventId) REFERENCES EVENTS(eventId),
    FOREIGN KEY (participantId) REFERENCES PARTICIPANTS(participantId)
)""")


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


@app.route("/events", methods=["POST"])
def create_event():
    if request.is_json:
        payload = dict(request.get_json())
        event_id = str(uuid.uuid4())
        title = payload.get("title", "Untitled Event")
        event_type = payload.get("type", "dates")
        selected_dates = json.dumps(payload.get("selectedDates", []))
        selected_days = json.dumps(payload.get("selectedDays", []))
        start_time = payload.get("startTime", "09:00")
        end_time = payload.get("endTime", "17:00")
        timezone = payload.get("timezone", "UTC")
        created_at = datetime.utcnow().isoformat()

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO EVENTS (eventId, title, type, selectedDates, selectedDays, startTime, endTime, timezone, createdAt)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, title, event_type, selected_dates, selected_days, start_time, end_time, timezone, created_at)
            )
            conn.commit()

        return jsonify({"eventId": event_id, "message": "Event created successfully"}), 201
    else:
        return jsonify({"error": "Request body must be json"}), 400


@app.route("/events/<event_id>", methods=["GET"])
def get_event(event_id):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM EVENTS WHERE eventId = ?", (event_id,))
        row = cursor.fetchone()

        if row:
            event = {
                "eventId": row[0],
                "title": row[1],
                "type": row[2],
                "selectedDates": json.loads(row[3]) if row[3] else [],
                "selectedDays": json.loads(row[4]) if row[4] else [],
                "startTime": row[5],
                "endTime": row[6],
                "timezone": row[7],
                "createdAt": row[8]
            }
            return jsonify(event), 200
        else:
            return jsonify({"error": "Event not found"}), 404


@app.route("/events/<event_id>/participants", methods=["GET"])
def get_participants(event_id):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT participantId, name, joinedAt FROM PARTICIPANTS WHERE eventId = ?", (event_id,))
        rows = cursor.fetchall()

        participants = [{"participantId": row[0], "name": row[1], "joinedAt": row[2]} for row in rows]
        return jsonify(participants), 200


@app.route("/events/<event_id>/participants", methods=["POST"])
def add_participant(event_id):
    if request.is_json:
        payload = dict(request.get_json())
        participant_id = str(uuid.uuid4())
        name = payload.get("name")
        joined_at = datetime.utcnow().isoformat()

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO PARTICIPANTS (participantId, eventId, name, joinedAt) VALUES (?, ?, ?, ?)",
                (participant_id, event_id, name, joined_at)
            )
            conn.commit()

        return jsonify({"participantId": participant_id, "message": "Participant added successfully"}), 201
    else:
        return jsonify({"error": "Request body must be json"}), 400


@app.route("/events/<event_id>/votes", methods=["GET"])
def get_votes(event_id):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT voteId, participantId, timeSlot FROM VOTES WHERE eventId = ?", (event_id,))
        rows = cursor.fetchall()

        votes = [{"voteId": row[0], "participantId": row[1], "timeSlot": row[2]} for row in rows]
        return jsonify(votes), 200


@app.route("/events/<event_id>/votes", methods=["POST"])
def add_vote(event_id):
    if request.is_json:
        payload = dict(request.get_json())
        participant_id = payload.get("participantId")
        time_slots = payload.get("timeSlots", [])

        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            # Delete existing votes for this participant
            cursor.execute("DELETE FROM VOTES WHERE eventId = ? AND participantId = ?", (event_id, participant_id))

            # Insert new votes
            for time_slot in time_slots:
                vote_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO VOTES (voteId, eventId, participantId, timeSlot) VALUES (?, ?, ?, ?)",
                    (vote_id, event_id, participant_id, time_slot)
                )
            conn.commit()

        return jsonify({"message": "Votes recorded successfully"}), 201
    else:
        return jsonify({"error": "Request body must be json"}), 400


if __name__ == "__main__":
    app.run(debug=False, port=10000)
