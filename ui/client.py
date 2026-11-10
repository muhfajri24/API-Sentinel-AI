"""Local controller transport with bounded timeouts and public-safe error messages."""

import json
import httpx
from urllib.parse import urlsplit


class ControllerError(Exception):
    pass


def request_api(controller: str, path: str, payload: dict | None = None) -> dict:
    try:
        url = urlsplit(controller)
        port = url.port
    except ValueError:
        raise ControllerError("Configure a valid loopback controller address.") from None
    if (
        not port
        or "\\" in controller
        or controller.strip() != controller
        or url.scheme != "http"
        or url.hostname != "127.0.0.1"
        or url.username
        or url.password
        or url.path not in ("", "/")
        or url.query
        or url.fragment
    ):
        raise ControllerError("Configure a loopback HTTP controller address.")
    try:
        with httpx.Client(timeout=40, trust_env=False, follow_redirects=False) as client:
            response = (
                client.get(controller.rstrip("/") + path)
                if payload is None
                else client.post(controller.rstrip("/") + path, json=payload)
            )
            if not response.is_success:
                messages = {
                    403: "Review and authorize the local test plan before execution.",
                    404: "The plan is missing or expired. Generate and review a new plan.",
                    413: "The input exceeds the local demo size limit.",
                    422: "Check the supported OpenAPI subset, synthetic payloads and rule. Fixture mode only supports the documented overdraft rule.",
                    429: "A local execution is already active. Wait for it to finish.",
                    502: "Meta could not return a valid plan. No fixture fallback was used.",
                    503: "Live model access or mode is not configured on the controller.",
                }
                raise ControllerError(
                    messages.get(
                        response.status_code,
                        "The local controller could not complete this request.",
                    )
                )
            if len(response.content) > 262144:
                raise ControllerError("Controller response exceeded the display limit.")
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("shape")
            return data
    except httpx.TimeoutException:
        raise ControllerError(
            "The local controller timed out. Check its terminal before retrying."
        ) from None
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        raise ControllerError(
            "Cannot read the local controller response. Check that its process is running."
        ) from None
