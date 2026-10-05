# -*- coding: utf-8 -*-
"""
TechAbout: Contact Inquiry API.

A small Flask API that receives contact-form inquiries and stores them in
SQLite.

Endpoints:
    POST /api/inquiries        Submit an inquiry {name, email, message}
    GET  /api/inquiries        List inquiries, filter with ?date=YYYY-MM-DD
                               or ?from=YYYY-MM-DD&to=YYYY-MM-DD
    GET  /api/inquiries/<id>   Fetch one inquiry
    GET  /api/health           Health check
    GET  /                     API documentation page

Run locally:
    pip install -r requirements.txt
    python app.py
"""
import os
import re
import sqlite3
from datetime import datetime, date

from flask import Flask, request, jsonify, render_template, g
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["DATABASE"] = os.environ.get("DATABASE_PATH", "inquiries.db")
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MB cap

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
MAX_NAME_LEN = 100
MAX_MESSAGE_LEN = 2000

SCHEMA = """
CREATE TABLE IF NOT EXISTS inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
    db.executescript(SCHEMA)
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_inquiry(data):
    """Return a list of error strings; empty list means valid."""
    errors = []
    if not isinstance(data, dict):
        return ["Request body must be a JSON object."]

    name = (data.get("name") or "")
    email = (data.get("email") or "")
    message = (data.get("message") or "")
    if not isinstance(name, str):
        name = ""
    if not isinstance(email, str):
        email = ""
    if not isinstance(message, str):
        message = ""
    name, email, message = name.strip(), email.strip(), message.strip()

    if not name:
        errors.append("name is required.")
    elif len(name) > MAX_NAME_LEN:
        errors.append("name must be at most %d characters." % MAX_NAME_LEN)

    if not email:
        errors.append("email is required.")
    elif not EMAIL_RE.match(email):
        errors.append("email '%s' is not a valid email address." % email)

    if not message:
        errors.append("message is required.")
    elif len(message) > MAX_MESSAGE_LEN:
        errors.append("message must be at most %d characters." % MAX_MESSAGE_LEN)

    return errors


def _parse_date_param(value, label, errors):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        errors.append("%s must be in YYYY-MM-DD format." % label)
        return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def docs():
    return render_template("docs.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/inquiries", methods=["POST"])
def submit_inquiry():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"errors": ["Request body must be valid JSON."]}), 400

    errors = validate_inquiry(data)
    if errors:
        return jsonify({"errors": errors}), 400

    created_at = datetime.utcnow().isoformat(timespec="seconds")
    db = get_db()
    cur = db.execute(
        "INSERT INTO inquiries (name, email, message, created_at)"
        " VALUES (?, ?, ?, ?)",
        (data["name"].strip(), data["email"].strip(),
         data["message"].strip(), created_at),
    )
    db.commit()
    inquiry_id = cur.lastrowid
    return jsonify({
        "id": inquiry_id,
        "name": data["name"].strip(),
        "email": data["email"].strip(),
        "message": data["message"].strip(),
        "created_at": created_at,
    }), 201


@app.route("/api/inquiries", methods=["GET"])
def list_inquiries():
    errors = []
    query = "SELECT id, name, email, message, created_at FROM inquiries"
    clauses = []
    params = []

    day = request.args.get("date")
    from_s = request.args.get("from")
    to_s = request.args.get("to")

    if day:
        d = _parse_date_param(day, "date", errors)
        if d:
            clauses.append("date(created_at) = date(?)")
            params.append(d.isoformat())
    if from_s:
        d = _parse_date_param(from_s, "from", errors)
        if d:
            clauses.append("date(created_at) >= date(?)")
            params.append(d.isoformat())
    if to_s:
        d = _parse_date_param(to_s, "to", errors)
        if d:
            clauses.append("date(created_at) <= date(?)")
            params.append(d.isoformat())

    if errors:
        return jsonify({"errors": errors}), 400

    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id ASC"

    rows = get_db().execute(query, params).fetchall()
    return jsonify({
        "count": len(rows),
        "inquiries": [dict(r) for r in rows],
    })


@app.route("/api/inquiries/<int:inquiry_id>", methods=["GET"])
def get_inquiry(inquiry_id):
    row = get_db().execute(
        "SELECT id, name, email, message, created_at FROM inquiries WHERE id = ?",
        (inquiry_id,)).fetchone()
    if row is None:
        return jsonify({"errors": ["Inquiry %d not found." % inquiry_id]}), 404
    return jsonify(dict(row))


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
