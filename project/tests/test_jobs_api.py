"""Create Job API, Job Status API, List API, Download API, Verification API."""
from uuid import UUID


def _create(env, payload) -> str:
    r = env.client.post("/api/v1/jobs", json=payload)
    assert r.status_code == 202, r.text
    return r.json()["job_id"]


def test_create_job_returns_immediately_with_pending_contract(env, payload):
    r = env.client.post("/api/v1/jobs", json=payload)
    body = r.json()
    assert r.status_code == 202
    assert body["status"] == "PENDING"  # response is built before background work runs
    assert body["message"] == "Certificate generation started"
    UUID(body["job_id"])  # valid uuid


def test_job_status_api(env, payload):
    job_id = _create(env, payload)
    r = env.client.get(f"/api/v1/jobs/{job_id}")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "COMPLETED"
    assert (body["total"], body["success"], body["failed"]) == (3, 3, 0)
    assert body["progress_percentage"] == 100
    assert body["failed_recipients"] == []


def test_job_status_not_found(env):
    r = env.client.get("/api/v1/jobs/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_list_certificates_with_pagination_filter_and_search(env, payload):
    job_id = _create(env, payload)
    url = f"/api/v1/jobs/{job_id}/certificates"

    all_ = env.client.get(url)
    assert all_.status_code == 200
    assert len(all_.json()) == 3
    assert all_.headers["X-Total-Count"] == "3"
    assert {"certificate_id", "recipient_name", "status"} <= set(all_.json()[0])

    page = env.client.get(url, params={"page": 2, "page_size": 2})
    assert len(page.json()) == 1 and page.headers["X-Total-Count"] == "3"

    found = env.client.get(url, params={"search": "john"})  # case-insensitive
    assert [c["recipient_name"] for c in found.json()] == ["John Doe"]

    assert env.client.get(url, params={"status": "FAILED"}).json() == []


def test_download_api_returns_pdf(env, payload):
    job_id = _create(env, payload)
    cert = env.client.get(f"/api/v1/jobs/{job_id}/certificates").json()[0]
    r = env.client.get(f"/api/v1/certificates/{cert['certificate_id']}/download")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_download_unknown_certificate_404(env):
    assert env.client.get("/api/v1/certificates/nope/download").status_code == 404


def test_verify_endpoint(env, payload):
    job_id = _create(env, payload)
    cert = env.client.get(f"/api/v1/jobs/{job_id}/certificates", params={"search": "John"}).json()[0]
    ok = env.client.get(f"/verify/{cert['certificate_id']}").json()
    assert ok["valid"] is True and ok["recipient"] == "John Doe"
    assert env.client.get("/verify/unknown-id").json() == {
        "valid": False, "recipient": None, "course_name": None,
        "event_name": None, "issue_date": None, "certificate_id": None,
    }


def test_health(env):
    r = env.client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "healthy"}
