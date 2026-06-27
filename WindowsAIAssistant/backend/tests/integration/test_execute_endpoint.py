from fastapi.testclient import TestClient

from backend.api import app


client = TestClient(app)


def test_execute_endpoint_returns_commands_and_logs() -> None:
    response = client.post(
        "/execute",
        json={
            "steps": ["Create a file named hello.txt", "Show the contents of the file"],
            "verify": True,
            "target_resource": ".",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["logs"]
    assert payload["commands"]
    assert any("hello.txt" in command["command"] for command in payload["commands"])
