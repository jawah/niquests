from __future__ import annotations

import pytest
from flask import Flask, jsonify, request
from flask import Response as FlaskResponse

from niquests import RetryConfiguration, Session
from niquests.packages.urllib3.contrib.webextensions.sse import ServerSentEvent

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


@app.route("/sse-events")
def sse_events():
    def generate():
        for i in range(3):
            yield f"event: message\ndata: event {i}\nid: {i}\n\n"
        yield "event: done\ndata: finished\n\n"

    return FlaskResponse(generate(), mimetype="text/event-stream")


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


def test_wsgi_sse():
    with Session(app=app) as s:
        resp = s.get("sse://default/sse-events")
        assert resp.status_code == 200

        ext = resp.extension
        assert ext is not None
        assert ext.closed is False

        events = []
        while True:
            event = ext.next_payload()
            if event is None:
                break
            assert isinstance(event, ServerSentEvent)
            events.append(event)

        assert len(events) == 4
        assert events[0].data == "event 0"
        assert events[0].event == "message"
        assert events[0].id == "0"
        assert events[3].event == "done"
        assert events[3].data == "finished"
        assert ext.closed is True


def test_wsgi_sse_send_forbidden():
    with Session(app=app) as s:
        resp = s.get("sse://default/sse-events")
        ext = resp.extension

        with pytest.raises(NotImplementedError):
            ext.send_payload("nope")

        ext.close()


def test_wsgi_sse_close():
    with Session(app=app) as s:
        resp = s.get("sse://default/sse-events")
        ext = resp.extension

        # Read one event then close early
        event = ext.next_payload()
        assert isinstance(event, ServerSentEvent)

        ext.close()
        assert ext.closed is True


def test_wsgi_websocket_not_supported():
    from niquests.packages.urllib3.exceptions import MaxRetryError

    with Session(app=app) as s:
        with pytest.raises(MaxRetryError) as exc_info:
            s.get("ws://default/ws-echo")
        assert isinstance(exc_info.value.reason, NotImplementedError)
        assert "WebSocket is not supported over WSGI" in str(exc_info.value.reason)
