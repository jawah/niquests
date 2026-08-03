from __future__ import annotations

import pytest

from niquests import Session


@pytest.mark.usefixtures("requires_traefik_tls")
class TestMultiplexed:
    @pytest.fixture(autouse=True)
    def configure_local_stack(self, local_httpbin, traefik_resolver, traefik_ca_bundle):
        self.httpbin = local_httpbin
        self.session_kwargs = {"resolver": traefik_resolver, "verify": traefik_ca_bundle}

    def test_concurrent_request_in_sync(self):
        responses = []

        with Session(multiplexed=True, **self.session_kwargs) as s:
            responses.append(s.get(f"{self.httpbin.https_url}/delay/3"))
            responses.append(s.get(f"{self.httpbin.https_url}/delay/1"))
            responses.append(s.get(f"{self.httpbin.https_url}/delay/1"))
            responses.append(s.get(f"{self.httpbin.https_url}/delay/3"))

            assert all(r.lazy for r in responses)

            s.gather()

        assert all(r.lazy is False for r in responses)
        assert all(r.status_code == 200 for r in responses)

    def test_redirect_with_multiplexed(self):
        with Session(multiplexed=True, **self.session_kwargs) as s:
            resp = s.get(f"{self.httpbin.https_url}/redirect/3")
            assert resp.lazy
            s.gather()

            assert resp.status_code == 200
            assert resp.url == f"{self.httpbin.https_url}/get"
            assert len(resp.history) == 3

    def test_redirect_with_multiplexed_direct_access(self):
        with Session(multiplexed=True, **self.session_kwargs) as s:
            resp = s.get(f"{self.httpbin.https_url}/redirect/3")
            assert resp.lazy

            assert resp.status_code == 200
            assert resp.url == f"{self.httpbin.https_url}/get"
            assert len(resp.history) == 3
            assert resp.json()

    def test_lazy_access_sync_mode(self):
        with Session(multiplexed=True, **self.session_kwargs) as s:
            resp = s.get(f"{self.httpbin.https_url}/headers")
            assert resp.lazy

            assert resp.status_code == 200

    def test_post_data_with_multiplexed(self):
        responses = []

        with Session(multiplexed=True, **self.session_kwargs) as s:
            for i in range(5):
                responses.append(
                    s.post(
                        f"{self.httpbin.https_url}/post",
                        data=b"foo" * 128,
                    )
                )

            s.gather()

        assert all(r.lazy is False for r in responses)
        assert all(r.status_code == 200 for r in responses)
        assert all(r.json()["data"] != "" for r in responses)

    def test_get_stream_with_multiplexed(self):
        with Session(multiplexed=True, **self.session_kwargs) as s:
            resp = s.get(f"{self.httpbin.https_url}/headers", stream=True)
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

        with Session(multiplexed=True, **self.session_kwargs) as s:
            for _ in [3, 1, 3, 5]:
                responses.append(s.get(f"{self.httpbin.https_url}/delay/{_}"))

            assert all(r.lazy for r in responses)
            promise_count = len(responses)

            while any(r.lazy for r in responses):
                s.gather(max_fetch=1)
                promise_count -= 1

                assert len(list(filter(lambda r: r.lazy, responses))) == promise_count

            assert len(list(filter(lambda r: r.lazy, responses))) == 0

    def test_early_close_no_error(self):
        responses = []

        with Session(multiplexed=True, **self.session_kwargs) as s:
            for _ in [2, 1, 1]:
                responses.append(s.get(f"{self.httpbin.https_url}/delay/{_}"))

            assert all(r.lazy for r in responses)

        # since urllib3.future 2.5, the scheduler ensure we kept track of ongoing request even if pool is
        # shutdown.
        assert all([r.json() for r in responses])


@pytest.mark.usefixtures("requires_wan")
def test_multiplexed_early_response() -> None:
    received_early_response: bool = False

    def callback_on_early(early_resp) -> None:
        nonlocal received_early_response
        if early_resp.status_code == 103:
            received_early_response = True

    with Session(multiplexed=True) as s:
        resp = s.get(
            "https://early-hints.fastlylabs.com/",
            hooks={"early_response": [callback_on_early]},
        )

        assert received_early_response is False

        assert resp.status_code == 200
        assert received_early_response is True
