# Sistema de Controle de Ferramentas

Aplicação web corporativa em Flask para controle de inventário, custódia, transferências, ocorrências, assinaturas internas, relatórios, notificações e auditoria de ferramentas.

## Estado atual

MVP implementado:

- Flask App Factory;
- configuração por ambiente e `.env`;
- SQLAlchemy 2.x, Flask-SQLAlchemy, Alembic/Flask-Migrate;
- SQL Server via `pyodbc`;
- autenticação Microsoft Entra ID/Azure AD com MSAL;
- autorização por usuário local no banco;
- Flask-Login;
- RBAC com perfis e permissões;
- escopos ABAC por usuário;
- cadastros administrativos;
- categorias, locais e ferramentas;
- foto de referência, QR Code e etiqueta;
- custódia atual e linha do tempo;
- transferências com aceite;
- inventários, itens e evidências;
- divergências e trava de finalização;
- ocorrências operacionais e patrimoniais;
- assinaturas internas;
- auditoria;
- relatórios e exportações CSV/Excel;
- dashboard;
- notificações internas sem Redis;
- envio de e-mail via Brasif Gateway Microsoft Graph, sem SMTP;
- comandos Flask CLI agendáveis;
- documentação técnica, operacional e de homologação;
- Pytest, Ruff, Docker, coverage, scripts de validação e GitHub Actions CI.

## Documentação

A documentação completa está em [`docs/`](docs/README.md).

Leitura recomendada:

- [Instalação local](docs/01-instalacao-local.md)
- [Docker](docs/02-docker.md)
- [Configuração Microsoft Entra ID](docs/03-configuracao-microsoft-entra-id.md)
- [Variáveis de ambiente](docs/04-variaveis-ambiente.md)
- [Migrations e banco](docs/05-migrations-e-banco.md)
- [Matriz de permissões](docs/08-matriz-de-permissoes.md)
- [Guia operacional](docs/09-guia-operacional.md)
- [Critérios de aceite](docs/11-criterios-de-aceite.md)
- [Troubleshooting](docs/12-troubleshooting.md)
- [Revisão de segurança](docs/13-revisao-de-seguranca.md)
- [Homologação final](docs/14-homologacao-final.md)
- [Plano de produção](docs/15-plano-producao.md)

## Requisitos locais

- Python 3.12+
- SQL Server acessível
- ODBC Driver 17 for SQL Server
- Docker, opcional

## Instalação local no Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edite o `.env` antes de rodar.

## Banco e permissões

```powershell
flask --app manage.py db upgrade
flask --app manage.py access-seed
```

Criar primeiro administrador:

```powershell
flask --app manage.py user-create --email seu.email@brasif.com.br --name "Seu Nome"
flask --app manage.py user-grant-role --email seu.email@brasif.com.br --role admin_sistema
flask --app manage.py user-grant-scope --email seu.email@brasif.com.br --scope-type global --scope-value=*
```

No PowerShell, use `--scope-value=*` para evitar expansão do `*`.

## Rodar localmente

```powershell
flask --app manage.py run --debug
```

Acesse:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/healthz`
- `http://127.0.0.1:5000/readyz`
- `http://127.0.0.1:5000/auth/login`

## Callback Microsoft

O callback canônico do sistema é:

```text
/auth/callback
```

Em desenvolvimento, cadastre no Microsoft Entra ID exatamente a URL configurada em `AUTH_MICROSOFT_REDIRECT_URI`, por exemplo:

```text
http://localhost:5000/auth/callback
```

ou:

```text
http://127.0.0.1:5000/auth/callback
```

## Rodar com Docker

```powershell
copy .env.example .env
docker compose build
docker compose up -d
```

Acesse:

- `http://127.0.0.1:8000/`

## Testes e lint

```powershell
python scripts/quality_gate.py
```

Ou etapa por etapa:

```powershell
ruff check .
python -m compileall -q app tests scripts
python -m pytest -q
```

## Comandos úteis

```powershell
flask --app manage.py db-info
flask --app manage.py db-ping
flask --app manage.py db current
flask --app manage.py access-list-roles
flask --app manage.py access-list-user --email usuario@brasif.com.br
flask --app manage.py notifications-scan
flask --app manage.py notifications-send-pending --dry-run
```

## Rotas principais

- `/admin/dashboard/`
- `/admin/tools/`
- `/admin/categories/`
- `/admin/locations/`
- `/admin/users/`
- `/admin/custody/`
- `/admin/transfers/`
- `/admin/inventories/`
- `/admin/occurrences/`
- `/admin/signatures/`
- `/admin/reports/`
- `/admin/notifications/`

## Observações importantes

- O Azure autentica, mas o BD autoriza
- Usuários sem cadastro local, inativos, bloqueados ou removidos logicamente não acessam
- Permissões são validadas no backend
- E-mail corporativo deve ser enviado pelo Brasif Gateway Microsoft Graph, nunca por SMTP
- Ações críticas registram auditoria, assinatura ou linha do tempo, conforme o módulo
- Não use `.is_(True)`/`.is_(False)` em queries booleanas do SQL Server. Use `== true()`/`== false()`
- Não rode `flask db init`. O diretório `migrations/` já é versionado
