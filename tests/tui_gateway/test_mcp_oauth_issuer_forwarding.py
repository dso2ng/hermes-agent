"""Browser callback ingress must preserve RFC 9207 issuer evidence for the SDK."""

import asyncio
from urllib.parse import urlencode

import httpx
import pytest

from hermes_constants import get_hermes_home
from tools.mcp_dashboard_oauth import DashboardOAuthFlow, dashboard_oauth_flow
from tools.mcp_oauth import _make_callback_waiter
from tui_gateway import mcp_oauth_sessions as sessions


@pytest.mark.parametrize("surface", ["dashboard", "loopback", "rpc"])
@pytest.mark.parametrize("issuer", [None, "https://idp.example/tenant%2Fone/", "https://other.example/"])
def test_callback_ingress_preserves_issuer_for_sdk(monkeypatch, surface, issuer):
    flow = DashboardOAuthFlow(
        "issuer-flow", "reports", None, str(get_hermes_home()),
        "http://127.0.0.1:49152/callback",
    )
    asyncio.run(flow.publish_authorization_url("https://idp.example/authorize?state=expected"))
    monkeypatch.setattr(sessions, "_sessions", {
        flow.flow_id: {"flow": flow, "server_name": flow.server_name, "hermes_home": flow.hermes_home},
    })
    listener = None
    client = None
    if surface == "dashboard":
        from fastapi import FastAPI
        from starlette.testclient import TestClient
        from hermes_cli.web_routers import mcp

        monkeypatch.setattr(mcp, "_mcp_oauth_flows", {flow.flow_id: flow})
        app = FastAPI()
        app.include_router(mcp.router)
        client = TestClient(app)
        url = "/api/mcp/oauth/callback/reports"
    elif surface == "loopback":
        listener = sessions._start_loopback_listener(flow)
        client = httpx.Client(trust_env=False, timeout=5)
        url = f"http://127.0.0.1:{listener.server_address[1]}/callback"

    def deliver(state):
        params = {"code": "test-code", "state": state}
        if issuer is not None:
            params["iss"] = issuer
        if surface == "rpc":
            from tui_gateway import server

            response = server.handle_request({
                "jsonrpc": "2.0", "id": 1, "method": "mcp.servers.oauth.callback",
                "params": {"session_id": flow.flow_id, "name": flow.server_name, **params},
            })
            assert "error" not in response, response
            return response["result"]["ok"]
        return client.get(url + "?" + urlencode(params)).status_code == 200

    try:
        assert not deliver("wrong-state")
        assert not flow._callback_ready.is_set()
        assert deliver("expected")
        assert not deliver("expected")
        with dashboard_oauth_flow(flow):
            result = asyncio.run(_make_callback_waiter(0)())
        assert (result.code, result.state, result.iss) == ("test-code", "expected", issuer)
    finally:
        if client is not None:
            client.close()
        if listener is not None:
            listener.shutdown()
            listener.server_close()
