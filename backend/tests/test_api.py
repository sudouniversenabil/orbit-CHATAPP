"""Smoke tests for REST and WebSocket API surfaces."""

from fastapi.testclient import TestClient

from backend.app.main import app


def test_rest_endpoints_expose_health_models_commands_and_local_chat() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        assert {item["id"] for item in client.get("/models").json()} >= {"ollama", "openai", "anthropic", "gemini"}
        assert client.get("/commands").status_code == 200
        response = client.post(
            "/chat",
            json={"messages": [{"role": "user", "content": "what time is it?"}]},
        )
        assert response.status_code == 200
        assert response.json()["command_handled"] is True
        assert "It is" in response.json()["response"]


def test_websocket_streams_a_routed_command_reply() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/voice") as websocket:
            websocket.send_json({"type": "text", "text": "system status"})
            events = []
            while not events or events[-1]["type"] != "assistant_done":
                events.append(websocket.receive_json())
            assert [event["type"] for event in events] == ["assistant_start", "token", "assistant_done"]
            assert "CPU:" in events[1]["text"]
