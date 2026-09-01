from __future__ import annotations

from app.db.session import transactional_session
from app.extensions import db
from app.models.system import SystemInfoModel


def test_database_extension_is_registered(app):
    with app.app_context():
        assert db.engine.dialect.name == "sqlite"


def test_system_info_model_can_be_persisted(app):
    with app.app_context():
        record = SystemInfoModel(
            chave="schema_version",
            valor="bloco-1",
            descricao="Registro técnico usado para validar a base de dados.",
        )
        db.session.add(record)
        db.session.commit()

        saved = db.session.execute(
            db.select(SystemInfoModel).where(SystemInfoModel.chave == "schema_version")
        ).scalar_one()

        assert saved.id_system_info is not None
        assert saved.created_at is not None
        assert saved.updated_at is not None
        assert saved.is_deleted is False


def test_transactional_session_commits(app):
    with app.app_context():
        with transactional_session() as session:
            session.add(SystemInfoModel(chave="transaction_test", valor="ok"))

        saved = db.session.execute(
            db.select(SystemInfoModel).where(
                SystemInfoModel.chave == "transaction_test"
            )
        ).scalar_one()

        assert saved.valor == "ok"


def test_db_ping_cli(app):
    runner = app.test_cli_runner()

    result = runner.invoke(args=["db-ping"])

    assert result.exit_code == 0
    assert "Banco respondeu com sucesso" in result.output
