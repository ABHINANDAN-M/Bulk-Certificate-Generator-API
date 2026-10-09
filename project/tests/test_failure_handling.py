"""One failed certificate must not stop the others."""
from tests.conftest import FlakyGenerator, TEMPLATE


def test_individual_failure_does_not_stop_job(make_env, payload):
    env = make_env(generator=FlakyGenerator(TEMPLATE))
    payload["recipients"].insert(1, {"name": "Will Fail", "email": "fail@example.com"})

    job_id = env.client.post("/api/v1/jobs", json=payload).json()["job_id"]
    status = env.client.get(f"/api/v1/jobs/{job_id}").json()

    assert status["status"] == "COMPLETED"           # others succeeded
    assert (status["total"], status["success"], status["failed"]) == (4, 3, 1)
    assert status["progress_percentage"] == 100
    assert status["failed_recipients"] == [
        {
            "recipient_name": "Will Fail",
            "email": "fail@example.com",
            "error_message": "RuntimeError: simulated rendering error",
        }
    ]


def test_failed_certificate_listed_but_not_downloadable(make_env, payload):
    env = make_env(generator=FlakyGenerator(TEMPLATE))
    payload["recipients"] = [{"name": "Will Fail", "email": "fail@example.com"},
                             {"name": "Good Person", "email": "good@example.com"}]
    job_id = env.client.post("/api/v1/jobs", json=payload).json()["job_id"]

    certs = env.client.get(f"/api/v1/jobs/{job_id}/certificates").json()
    failed = next(c for c in certs if c["status"] == "FAILED")
    assert failed["error_message"]
    assert env.client.get(f"/api/v1/certificates/{failed['certificate_id']}/download").status_code == 404
    assert env.client.get(f"/verify/{failed['certificate_id']}").json()["valid"] is False


def test_job_marked_failed_when_every_certificate_fails(make_env, payload):
    env = make_env(generator=FlakyGenerator(TEMPLATE))
    payload["recipients"] = [{"name": "Fail One", "email": "a@example.com"},
                             {"name": "Fail Two", "email": "b@example.com"}]
    job_id = env.client.post("/api/v1/jobs", json=payload).json()["job_id"]
    status = env.client.get(f"/api/v1/jobs/{job_id}").json()
    assert status["status"] == "FAILED" and status["failed"] == 2
