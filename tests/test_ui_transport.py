import pytest
from ui.client import request_api, ControllerError


@pytest.mark.parametrize(
    "origin",
    [
        "https://external.test",
        "http://127.0.0.1:bad",
        "http://127.0.0.1:8100/private",
        "http://user:password@127.0.0.1:8100",
    ],
)
def test_ui_controller_address_rejected_before_network(origin):
    with pytest.raises(ControllerError):
        request_api(origin, "/health")


def test_controller_oversize_response_is_stopped_while_streaming(monkeypatch):
    import httpx
    import ui.client

    consumed = []

    class Body(httpx.SyncByteStream):
        def __iter__(self):
            for i in range(1000):
                consumed.append(i)
                yield b"x" * 16384

    transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=Body()))
    real_client = httpx.Client
    monkeypatch.setattr(
        ui.client.httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    with pytest.raises(ControllerError, match="display limit"):
        request_api("http://127.0.0.1:8100", "/health")
    assert len(consumed) < 20


def test_target_change_invalidates_prior_consent_and_plan():
    from ui.state import input_fingerprint, synchronize_inputs

    old = input_fingerprint("{}", "rule", "controller", "fixture", "http://127.0.0.1:8101")
    state = {
        "input_fingerprint": old,
        "authorized": True,
        "reviewed": True,
        "plan": {},
        "receipt": {},
    }
    new = input_fingerprint("{}", "rule", "controller", "fixture", "http://127.0.0.1:8102")
    synchronize_inputs(state, new)
    assert state == {"input_fingerprint": new}
