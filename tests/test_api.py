# -*- coding: utf-8 -*-
"""Automated tests for the Contact Inquiry API."""
import os
import tempfile

import pytest

import app as app_module


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app_module.app.config["DATABASE"] = path
    app_module.app.config["TESTING"] = True
    app_module.init_db()
    with app_module.app.test_client() as client:
        yield client
    os.unlink(path)


def submit(client, payload):
    return client.post("/api/inquiries", json=payload)


VALID = {"name": "Ahmed Khan", "email": "ahmed@example.com",
         "message": "Please send a quote."}


# --- Submit ---------------------------------------------------------------
def test_submit_valid_returns_201(client):
    resp = submit(client, VALID)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["name"] == "Ahmed Khan"
    assert body["email"] == "ahmed@example.com"
    assert "created_at" in body


def test_submit_missing_name(client):
    resp = submit(client, {"email": "a@b.com", "message": "hi"})
    assert resp.status_code == 400
    assert any("name" in e for e in resp.get_json()["errors"])


def test_submit_invalid_email(client):
    resp = submit(client, {"name": "Ali", "email": "not-an-email",
                           "message": "hi"})
    assert resp.status_code == 400
    assert any("email" in e for e in resp.get_json()["errors"])


def test_submit_missing_message(client):
    resp = submit(client, {"name": "Ali", "email": "a@b.com"})
    assert resp.status_code == 400
    assert any("message" in e for e in resp.get_json()["errors"])


def test_submit_non_json_body(client):
    resp = client.post("/api/inquiries", data="plain text",
                       content_type="text/plain")
    assert resp.status_code == 400


def test_submit_message_too_long(client):
    payload = dict(VALID, message="x" * 2001)
    resp = submit(client, payload)
    assert resp.status_code == 400


def test_submit_trims_whitespace(client):
    payload = {"name": "  Ali  ", "email": "a@b.com", "message": " hi "}
    resp = submit(client, payload)
    assert resp.get_json()["name"] == "Ali"


# --- List ------------------------------------------------------------------
def test_list_returns_submitted(client):
    submit(client, VALID)
    submit(client, {"name": "Sara", "email": "s@b.com", "message": "hello"})
    resp = client.get("/api/inquiries")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 2
    assert body["inquiries"][0]["name"] == "Ahmed Khan"


def test_list_empty(client):
    resp = client.get("/api/inquiries")
    assert resp.get_json() == {"count": 0, "inquiries": []}


def test_list_filter_by_date(client):
    submit(client, VALID)
    today = resp_today(client)
    resp = client.get("/api/inquiries?date=" + today)
    assert resp.get_json()["count"] == 1
    resp = client.get("/api/inquiries?date=2000-01-01")
    assert resp.get_json()["count"] == 0


def resp_today(client):
    body = client.get("/api/inquiries").get_json()
    return body["inquiries"][0]["created_at"][:10]


def test_list_filter_by_range(client):
    submit(client, VALID)
    resp = client.get("/api/inquiries?from=2000-01-01&to=2100-01-01")
    assert resp.get_json()["count"] == 1
    resp = client.get("/api/inquiries?from=2100-01-01&to=2200-01-01")
    assert resp.get_json()["count"] == 0


def test_list_bad_date_format(client):
    resp = client.get("/api/inquiries?date=05-10-2026")
    assert resp.status_code == 400
    assert resp.get_json()["errors"]


# --- Single fetch -----------------------------------------------------------
def test_get_one_inquiry(client):
    created = submit(client, VALID).get_json()
    resp = client.get("/api/inquiries/%d" % created["id"])
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "ahmed@example.com"


def test_get_missing_inquiry_404(client):
    resp = client.get("/api/inquiries/999")
    assert resp.status_code == 404


# --- Docs and health ---------------------------------------------------------
def test_docs_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Contact Inquiry API" in resp.data


def test_health(client):
    resp = client.get("/api/health")
    assert resp.get_json() == {"status": "ok"}
