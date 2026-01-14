from __future__ import annotations

from flask import Flask, jsonify, request

from niquests import Session

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


def test_asgi_basic():
    with Session(app=app) as s:
        resp = s.get("/hello?foo=bar")
        assert resp.status_code == 200
        assert resp.json()["path"] == "/hello"


def test_asgi_stream_response():
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
