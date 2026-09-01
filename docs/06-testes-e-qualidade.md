# Testes e qualidade

## Ferramentas

- Pytest
- pytest-cov
- Ruff lint
- Ruff format check
- Compileall
- GitHub Actions CI
- Docker build

## Quality gate local

Rode a validação completa local:

```powershell
python scripts/quality_gate.py
```

Incluindo build Docker:

```powershell
python scripts/quality_gate.py --include-docker
```

Apenas compile/lint, sem testes:

```powershell
python scripts/quality_gate.py --skip-tests
```

## Rodar etapa por etapa

```powershell
ruff check .
python -m compileall -q app tests scripts
python -m pytest -q
```

Com coverage:

```powershell
python -m pytest --cov=app --cov-report=term-missing:skip-covered
```

## Rodar arquivo específico

```powershell
python -m pytest tests/test_notifications.py -q
python -m pytest tests/test_inventory_divergences.py -q
python -m pytest tests/test_signature_services.py -q
```

## Rodar teste específico

```powershell
python -m pytest tests/test_notifications.py::test_notifications_page_renders_for_admin -q
```

## Formatar

```powershell
ruff format .
```

## Corrigir imports e problemas seguros

```powershell
ruff check . --fix
```

## CI

O pipeline em `.github/workflows/ci.yml` executa:

1. instalação de dependências de sistema para `pyodbc`;
2. instalação do `requirements.txt`;
3. `ruff check .`;
4. `python -m compileall -q app tests scripts`;
5. `python -m pytest --cov=app`;
6. build Docker com `docker compose build`.

## Cuidados com SQL Server

Os testes rodam em SQLite para velocidade e isolamento, mas o runtime real usa SQL Server. Por isso:

- não use sintaxe SQL não compatível;
- não confie apenas no SQLite para validar queries críticas;
- para booleanos, use `== true()` e `== false()`;
- evite cascades agressivos;
- valide migrations contra SQL Server antes de homologar;
- valide `db upgrade` em ambiente de homologação conectado ao SQL Server.

## Migrations

A suíte inclui teste de integridade da cadeia Alembic:

```powershell
python -m pytest tests/test_production_readiness.py -q
```

Esse teste valida:

- revisions únicas;
- uma única migration raiz;
- uma única head;
- `down_revision` apontando para revision existente.

Ele não substitui `flask --app manage.py db upgrade` em SQL Server.

## Cobertura recomendada

Priorize testes para regras de risco:

- usuário não cadastrado não acessa;
- usuário inativo/bloqueado não acessa;
- permissões no backend;
- escopos;
- ferramenta criada com unicidade;
- alteração crítica gera auditoria;
- ferramenta ativa não pode ter duas custódias atuais;
- transferência recusada preserva custódia;
- transferência concluída não pode ser cancelada;
- inventário com divergência não finaliza;
- divergência regularizada exige ação real;
- ocorrência de baixa encerra custódia;
- usuário inativo não assina;
- relatórios respeitam escopo;
- exportações sanitizam CSV/XLSX;
- gateway de e-mail não registra segredo.

## Checklist antes de commit

```powershell
python scripts/quality_gate.py
flask --app manage.py db current
```

## Checklist antes de deploy

```powershell
python scripts/quality_gate.py --include-docker
flask --app manage.py db upgrade
flask --app manage.py access-seed
flask --app manage.py db-ping
```

Depois execute o checklist de [homologação final](14-homologacao-final.md).
