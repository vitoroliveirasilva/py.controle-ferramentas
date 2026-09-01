from __future__ import annotations


def test_app_factory_loads_testing_config(app):
    assert app.config["TESTING"] is True
    assert app.config["APP_ENV"] == "testing"


def test_index_page_renders(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Controle de ferramentas" in response.get_data(as_text=True)
