from __future__ import annotations

from flask import Flask, jsonify, request

from niquests import RetryConfiguration, Session

app = Flask(__name__)


@app.route("/hello")
def hello():
    return jsonify(
        {
            "method": request.method,
            "path": request.path,
            "query": request.query_string.decode("utf-8"),
            "message": "hello from wsgi",
        }
    )


@app.route("/retries")
def retries():
    # Use a simple counter stored in app config
    if not hasattr(app, "_retry_count"):
        app._retry_count = 0

    app._retry_count += 1

    if app._retry_count == 1:
        return jsonify({"error": "temporary failure"}), 503

    # Reset for next test
    count = app._retry_count
    app._retry_count = 0
    return jsonify({"message": "success", "attempts": count}), 200


@app.route("/echo", methods=["GET", "POST", "PUT", "DELETE"])
def echo():
    return jsonify(
        {
            "method": request.method,
            "path": request.path,
            "query": request.query_string.decode("utf-8"),
            "body": request.get_data(as_text=True),
            "headers": dict(request.headers),
        }
    )


def test_wsgi_basic():
    with Session(app=app) as s:
        resp = s.get("/hello?foo=bar")
        assert resp.status_code == 200
        assert resp.json()["path"] == "/hello"


def test_wsgi_retries():
    with Session(app=app, retries=RetryConfiguration(total=1, status_forcelist=(503,))) as s:
        resp = s.get("/retries")
        assert resp.status_code == 200

        resp = s.get("/retries")
        assert resp.status_code == 200

    with Session(app=app) as s:
        resp = s.get("/retries")
        assert resp.status_code == 503


def test_wsgi_stream_response():
    with Session(app=app) as s:
        resp = s.post(
            "/echo",
            data=b"foobar" * 32,
            stream=True,
        )
        assert resp.status_code == 200
        assert resp.json()["path"] == "/echo"

        for chunk in resp.iter_content(6):
            ...
