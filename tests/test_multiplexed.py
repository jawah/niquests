from __future__ import annotations

import pytest

from niquests import Session


@pytest.mark.usefixtures("requires_wan")
class TestMultiplexed:
    def test_concurrent_request_in_sync(self):
        responses = []

        with Session(multiplexed=True) as s:
            responses.append(s.get("https://pie.dev/delay/3"))
            responses.append(s.get("https://pie.dev/delay/1"))
            responses.append(s.get("https://pie.dev/delay/1"))
            responses.append(s.get("https://pie.dev/delay/3"))

            assert all(r.lazy for r in responses)

            s.gather()

        assert all(r.lazy is False for r in responses)
        assert all(r.status_code == 200 for r in responses)

    def test_redirect_with_multiplexed(self):
        with Session(multiplexed=True) as s:
            resp = s.get("https://pie.dev/redirect/3")
            assert resp.lazy
            s.gather()

            assert resp.status_code == 200
            assert resp.url == "https://pie.dev/get"
            assert len(resp.history) == 3

    def test_redirect_with_multiplexed_direct_access(self):
        with Session(multiplexed=True) as s:
            resp = s.get("https://pie.dev/redirect/3")
            assert resp.lazy

            assert resp.status_code == 200
            assert resp.url == "https://pie.dev/get"
            assert len(resp.history) == 3
            assert resp.json()

    def test_lazy_access_sync_mode(self):
        with Session(multiplexed=True) as s:
            resp = s.get("https://pie.dev/headers")
            assert resp.lazy

            assert resp.status_code == 200

    def test_post_data_with_multiplexed(self):
        responses = []

        with Session(multiplexed=True) as s:
            for i in range(5):
                responses.append(
                    s.post(
                        "https://pie.dev/post",
                        data=b"foo" * 128,
                    )
                )

            s.gather()

        assert all(r.lazy is False for r in responses)
        assert all(r.status_code == 200 for r in responses)
        assert all(r.json()["data"] == "foo" * 128 for r in responses)

    def test_get_stream_with_multiplexed(self):
        with Session(multiplexed=True) as s:
            resp = s.get("https://pie.dev/headers", stream=True)
            assert resp.lazy

            assert resp.status_code == 200
            assert resp._content_consumed is False

            payload = b""

            for chunk in resp.iter_content(32):
                payload += chunk

            assert resp._content_consumed is True

            import json

            assert isinstance(json.loads(payload), dict)

    def test_one_at_a_time(self):
        responses = []

        with Session(multiplexed=True) as s:
            for _ in [3, 1, 3, 5]:
                responses.append(s.get(f"https://pie.dev/delay/{_}"))

            assert all(r.lazy for r in responses)
            promise_count = len(responses)

            while any(r.lazy for r in responses):
                s.gather(max_fetch=1)
                promise_count -= 1

                assert len(list(filter(lambda r: r.lazy, responses))) == promise_count

            assert len(list(filter(lambda r: r.lazy, responses))) == 0

    def test_early_close_no_error(self):
        responses = []

        with Session(multiplexed=True) as s:
            for _ in [2, 1, 1]:
                responses.append(s.get(f"https://pie.dev/delay/{_}"))

            assert all(r.lazy for r in responses)

        # since urllib3.future 2.5, the scheduler ensure we kept track of ongoing request even if pool is
        # shutdown.
        assert all([r.json() for r in responses])
