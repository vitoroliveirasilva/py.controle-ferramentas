# Execução com Docker

## Objetivo

Rodar a aplicação em container para desenvolvimento, homologação ou preparação de deploy.

## Pré-requisitos

- Docker Desktop instalado.
- Arquivo `.env` criado a partir de `.env.example`.
- SQL Server acessível pela rede do container.
   
## Comandos principais

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

No Windows PowerShell:

```powershell
copy .env.example .env
docker compose build
docker compose up -d
```

Acesse:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/healthz`
- `http://127.0.0.1:8000/readyz`

## Volume de uploads

O `docker-compose.yml` usa o volume nomeado abaixo para preservar evidências, fotos e anexos:

```text
controle-ferramentas-uploads:/app/instance/uploads
```

Se usar outro diretório, ajuste `UPLOAD_BASE_DIR` no `.env` e garanta persistência.

## Healthcheck

O compose valida `/healthz` dentro do container. Para verificar:

```powershell
docker compose ps
docker inspect controle-ferramentas-web --format='{{json .State.Health}}'
```

## Aplicar migrations pelo container

```bash
docker compose exec web flask --app manage.py db upgrade
docker compose exec web flask --app manage.py access-seed
docker compose exec web flask --app manage.py db-ping
```

Se o container ainda não estiver de pé, use `run`:

```bash
docker compose run --rm web flask --app manage.py db upgrade
docker compose run --rm web flask --app manage.py access-seed
```

## Criar administrador pelo container

```bash
docker compose exec web flask --app manage.py user-create --email seu.email@brasif.com.br --name "Seu Nome"
docker compose exec web flask --app manage.py user-grant-role --email seu.email@brasif.com.br --role admin_sistema
docker compose exec web flask --app manage.py user-grant-scope --email seu.email@brasif.com.br --scope-type global --scope-value=*
```

No PowerShell, use `--scope-value=*` para evitar expansão indevida do `*`.

## Testes pelo container

```bash
docker compose run --rm web python scripts/quality_gate.py
docker compose run --rm web ruff check .
docker compose run --rm web python -m pytest -q
```

## Logs

```powershell
docker compose logs -f web
```

## Parar

```powershell
docker compose down
```

Para remover também volumes locais, use apenas quando tiver certeza:

```powershell
docker compose down -v
```

## Observações

- O container expõe a porta `8000`
- A aplicação usa Gunicorn no container
- O SQL Server não está no `docker-compose.yml`, porque o alvo real é SQL Server
- Não versione `.env`
- Para produção, use HTTPS atrás de proxy reverso
- E-mail deve sair pelo Brasif Gateway Microsoft Graph, nunca por SMTP
