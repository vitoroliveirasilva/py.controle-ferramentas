# Instalação local

## Pré-requisitos

- Python 3.12 ou superior
- Git
- SQL Server acessível
- ODBC Driver 17 for SQL Server instalado
- PowerShell no Windows
- Docker Desktop, opcional

## Clonar e preparar ambiente

```powershell
git clone https://github.com/brasif/py.controle-ferramentas/
cd py.controle-ferramentas

python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

## Configurar `.env`

Edite o arquivo `.env` com:

```env
APP_ENV=development
SECRET_KEY=secret-key
SQLSERVER_HOST=servidor-sql
SQLSERVER_DATABASE=ControleFerramentas
SQLSERVER_USERNAME=usuario
SQLSERVER_PASSWORD=senha
SQLSERVER_TRUST_SERVER_CERTIFICATE=yes
AUTH_DEV_LOGIN_ENABLED=1
```

Para teste local sem Microsoft, `AUTH_DEV_LOGIN_ENABLED=1` permite login de desenvolvimento.

OBS: Nunca use isso em produção.

## Aplicar migrations

```powershell
flask --app manage.py db upgrade
```

## Popular permissões

```powershell
flask --app manage.py access-seed
```

## Criar primeiro administrador

```powershell
flask --app manage.py user-create --email seu.email@brasif.com.br --name "Seu Nome"
flask --app manage.py user-grant-role --email seu.email@brasif.com.br --role admin_sistema
flask --app manage.py user-grant-scope --email seu.email@brasif.com.br --scope-type global --scope-value=*
```

No PowerShell, prefira `--scope-value=*`, porque `*` separado pode ser expandido para nomes de arquivos da pasta.

## Rodar aplicação

```powershell
flask --app manage.py run --debug
```

Acesse:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/healthz`
- `http://127.0.0.1:5000/readyz`
- `http://127.0.0.1:5000/auth/login`

## Rodar testes e lint

```powershell
pytest
ruff check .
```

## Primeira navegação recomendada

1. Acesse `/auth/login`.
2. Entre com o e-mail cadastrado.
3. Acesse `/admin/dashboard/`.
4. Cadastre categorias.
5. Cadastre locais.
6. Cadastre ferramentas.
7. Defina custódia inicial.
8. Teste transferência.
9. Teste inventário.
