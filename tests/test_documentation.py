from __future__ import annotations

from pathlib import Path

REQUIRED_DOCS = (
    "docs/README.md",
    "docs/00-visao-geral.md",
    "docs/01-instalacao-local.md",
    "docs/02-docker.md",
    "docs/03-configuracao-microsoft-entra-id.md",
    "docs/04-variaveis-ambiente.md",
    "docs/05-migrations-e-banco.md",
    "docs/06-testes-e-qualidade.md",
    "docs/07-deploy.md",
    "docs/08-matriz-de-permissoes.md",
    "docs/09-guia-operacional.md",
    "docs/10-modulos.md",
    "docs/11-criterios-de-aceite.md",
    "docs/12-troubleshooting.md",
    "docs/13-revisao-de-seguranca.md",
)


def test_required_documentation_files_exist():
    missing = [path for path in REQUIRED_DOCS if not Path(path).is_file()]
    assert not missing


def test_readme_links_to_documentation_index():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "docs/README.md" in readme


def test_environment_documentation_uses_gateway_instead_of_smtp():
    env_example = Path(".env.example").read_text(encoding="utf-8")
    env_docs = Path("docs/04-variaveis-ambiente.md").read_text(encoding="utf-8")

    assert "BRASIF_GATEWAY_API_KEY" in env_example
    assert "BRASIF_GATEWAY_API_KEY" in env_docs
    assert "SMTP_HOST" not in env_example
    assert "SMTP_PASSWORD" not in env_docs
