# TechAbout: Contact Inquiry API

A small Python (Flask) API that receives contact-form inquiries and stores
them in SQLite.

## Endpoints

- `POST /api/inquiries` : submit `{name, email, message}`. Returns `201` with
  the stored inquiry, or `400` with an `errors` list.
- `GET /api/inquiries` : list inquiries (`count` + `inquiries`).
  Filters: `?date=YYYY-MM-DD`, `?from=YYYY-MM-DD&to=YYYY-MM-DD`.
- `GET /api/inquiries/<id>` : one inquiry, or `404`.
- `GET /api/health` : `{"status": "ok"}`.
- `GET /` : API documentation page with a live try-it form.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open http://127.0.0.1:5000 for the docs page.

Environment variables (see `.env.example`):

- `DATABASE_PATH`: SQLite file location (default `inquiries.db`).
- `PORT`: port to listen on (default 5000).

## Validation rules

- `name`: required, max 100 characters.
- `email`: required, must match a standard email pattern.
- `message`: required, max 2000 characters.
- Date filters must use `YYYY-MM-DD`.

## How it was tested

16 automated tests in `tests/test_api.py`, run with:

```bash
pytest -v
```

Coverage: valid submit (201 + stored fields), missing name, invalid email,
missing message, non-JSON body, over-long message, whitespace trimming,
listing, empty list, date filter, range filter, bad date format, single fetch,
404 for unknown id, docs page, health check. Tests use a temporary SQLite
file, so the real database is never touched.

Manual test: ran the server, submitted inquiries via curl and the docs page
form, verified listing and date filters.

## Limitations

- SQLite is a single file: fine for small volume, not for high concurrency.
- No authentication: anyone with the URL can submit and read inquiries.
- No pagination on the list endpoint.
- No spam protection (CAPTCHA / rate limiting) on the submit endpoint.
- Email addresses are validated by pattern only; no verification email is sent.
