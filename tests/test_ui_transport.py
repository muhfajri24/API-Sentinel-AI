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
