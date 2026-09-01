from __future__ import annotations


def test_404_html_response(client):
    response = client.get("/rota-inexistente")

    assert response.status_code == 404
    assert "Erro 404" in response.get_data(as_text=True)


def test_404_json_response(client):
    response = client.get("/rota-inexistente", headers={"Accept": "application/json"})

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"]["code"] == 404
