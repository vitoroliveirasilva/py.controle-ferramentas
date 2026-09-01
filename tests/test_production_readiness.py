from __future__ import annotations

import ast
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (ROOT_DIR / path).read_text(encoding="utf-8")


def _migration_metadata(path: Path) -> tuple[str, str | None]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    revision: str | None = None
    down_revision: str | None = None

    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        target_names = [
            target.id for target in node.targets if isinstance(target, ast.Name)
        ]
        if "revision" in target_names:
            revision = ast.literal_eval(node.value)
        if "down_revision" in target_names:
            down_revision = ast.literal_eval(node.value)

    assert revision, f"Migration sem revision: {path.name}"
    assert down_revision is None or isinstance(
        down_revision, str
    ), f"down_revision inválido: {path.name}"
    return revision, down_revision


def test_alembic_migration_chain_is_linear_and_complete():
    migration_files = sorted((ROOT_DIR / "migrations" / "versions").glob("*.py"))
    assert migration_files, "Nenhuma migration encontrada."

    metadata = [_migration_metadata(path) for path in migration_files]
    revisions = [revision for revision, _down_revision in metadata]
    down_revisions = [down_revision for _revision, down_revision in metadata]

    assert len(revisions) == len(
        set(revisions)
    ), "Há revisions duplicadas nas migrations."
    assert (
        down_revisions.count(None) == 1
    ), "A cadeia deve ter exatamente uma migration raiz."

    revision_set = set(revisions)
    for _revision, down_revision in metadata:
        if down_revision is not None:
            assert down_revision in revision_set

    heads = revision_set - {
        down_revision for down_revision in down_revisions if down_revision
    }
    assert len(heads) == 1, f"A cadeia deve ter uma única head. Heads: {sorted(heads)}"


def test_ci_runs_quality_tests_and_docker_build():
    ci = _read(".github/workflows/ci.yml")

    assert "ruff check ." in ci
    assert "python -m compileall -q app tests scripts" in ci
    assert "python -m pytest" in ci
    assert "docker compose build" in ci
    assert "unixodbc-dev" in ci


def test_docker_compose_has_healthcheck_and_persistent_upload_volume():
    compose = _read("docker-compose.yml")

    assert "healthcheck:" in compose
    assert "controle-ferramentas-uploads" in compose
    assert "/app/instance/uploads" in compose
    assert "APP_ENV:" in compose


def test_final_homologation_docs_are_linked():
    docs_index = _read("docs/README.md")
    root_readme = _read("README.md")

    assert "14-homologacao-final.md" in docs_index
    assert "14-homologacao-final.md" in root_readme
    assert "15-plano-producao.md" in docs_index
    assert "15-plano-producao.md" in root_readme


def test_environment_example_stays_gateway_only_for_email():
    env_example = _read(".env.example")

    assert "BRASIF_GATEWAY_API_KEY=" in env_example
    assert "BRASIF_GATEWAY_BASE_URL=https://howard.brasif.local" in env_example
    assert "SMTP_" not in env_example
    assert "MAIL_PASSWORD" not in env_example


def test_quality_gate_script_exists_and_documents_docker_option():
    script = _read("scripts/quality_gate.py")
    quality_doc = _read("docs/06-testes-e-qualidade.md")

    assert "--include-docker" in script
    assert "scripts/quality_gate.py --include-docker" in quality_doc
