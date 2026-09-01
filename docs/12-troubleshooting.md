# Troubleshooting

## `ModuleNotFoundError`

Instale dependências:

```powershell
pip install -r requirements.txt
```

## `flask` não encontrado

Ative o ambiente virtual:

```powershell
.\venv\Scripts\Activate.ps1
```

## PowerShell bloqueia ativação do venv

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## SQL Server não conecta

Teste:

```powershell
flask --app manage.py db-info
flask --app manage.py db-ping
```

Verifique:

- driver ODBC instalado;
- host e porta;
- usuário/senha;
- firewall;
- banco existente;
- `TrustServerCertificate=yes` em ambiente com certificado interno.

## `Incorrect syntax near '1'`

Provável uso de `.is_(True)` ou `.is_(False)` em campo BIT no SQL Server.

Use:

```python
from sqlalchemy import true, false

Model.ativo == true()
Model.is_deleted == false()
```

## `access-seed` não cria perfis

Rode:

```powershell
flask --app manage.py access-seed
flask --app manage.py access-list-roles
```

Se necessário, confira se a migration de permissões foi aplicada.

## PowerShell expande `*`

Use:

```powershell
flask --app manage.py user-grant-scope --email usuario@brasif.com.br --scope-type global --scope-value=*
```

Evite:

```powershell
--scope-value "*"
```

em alguns contextos, porque pode virar lista de arquivos.

## Login Microsoft retorna erro de callback

Verifique se `AUTH_MICROSOFT_REDIRECT_URI` bate exatamente com o App Registration e se `AUTH_MICROSOFT_REDIRECT_PATH` aponta para o mesmo caminho. O padrão recomendado é `/auth/callback`.

## Acesso negado após login

Verifique usuário local:

```powershell
flask --app manage.py access-list-user --email usuario@brasif.com.br
```

Corrija com:

```powershell
flask --app manage.py user-activate --email usuario@brasif.com.br
flask --app manage.py user-unblock --email usuario@brasif.com.br
flask --app manage.py user-grant-role --email usuario@brasif.com.br --role tecnico
```

## Upload falha

Verifique:

- extensão permitida;
- tamanho máximo;
- pasta `UPLOAD_BASE_DIR`;
- permissão de escrita no servidor;
- existência de `instance/uploads`.

## Template Jinja quebra com `expected token`

Procure tags quebradas como:

```jinja2
{% if status="" ="value" %}
```

Use comparação válida:

```jinja2
{% if status == value %}selected{% endif %}
```

## Exportação Excel falha

Garanta que `openpyxl` está instalado:

```powershell
pip install -r requirements.txt
```

## QR Code falha

Garanta que `qrcode[pil]` está instalado:

```powershell
pip install -r requirements.txt
```

## Testes passam, runtime SQL Server falha

O SQLite de teste pode aceitar sintaxes que o SQL Server rejeita. Valide queries críticas em SQL Server antes de homologar.
