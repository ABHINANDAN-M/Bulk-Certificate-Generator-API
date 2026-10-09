"""Validation rules: name, email, duplicates, empty list, max size."""
import pytest


def _post(env, payload):
    return env.client.post("/api/v1/jobs", json=payload)


def test_empty_recipient_list_rejected(env, payload):
    payload["recipients"] = []
    r = _post(env, payload)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("email", ["not-an-email", "missing@tld", "@example.com", ""])
def test_invalid_email_rejected(env, payload, email):
    payload["recipients"][0]["email"] = email
    assert _post(env, payload).status_code == 422


def test_duplicate_email_rejected_case_insensitive(env, payload):
    payload["recipients"][1]["email"] = "ABHI@gmail.com"  # same as recipient 0
    r = _post(env, payload)
    assert r.status_code == 422
    assert "Duplicate" in r.text


@pytest.mark.parametrize("name", ["", "ab", "  a "])
def test_name_too_short_rejected(env, payload, name):
    payload["recipients"][0]["name"] = name
    assert _post(env, payload).status_code == 422


def test_name_required(env, payload):
    del payload["recipients"][0]["name"]
    assert _post(env, payload).status_code == 422


def test_more_than_1000_recipients_rejected(env, payload):
    payload["recipients"] = [
        {"name": f"Person {i:04d}", "email": f"p{i}@example.com"} for i in range(1001)
    ]
    assert _post(env, payload).status_code == 422


def test_validation_failure_creates_no_job(env, payload):
    payload["recipients"] = []
    _post(env, payload)
    assert env.jobs.jobs == {}
