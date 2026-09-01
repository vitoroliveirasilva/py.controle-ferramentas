# Variáveis de ambiente

## Aplicação

| Variável | Uso |
|---|---|
| `PROJECT_NAME` | Nome exibido da aplicação |
| `APP_VERSION` | Versão lógica do app |
| `APP_ENV` | `development`, `testing` ou `production` |
| `FLASK_DEBUG` | Debug local |
| `SECRET_KEY` | Chave de sessão e CSRF (Deve ser forte em produção) |
| `WTF_CSRF_ENABLED` | Liga/desliga CSRF |

## Servidor

| Variável | Uso |
|---|---|
| `SERVER_HOST` | Host local |
| `SERVER_PORT` | Porta local |
| `LOG_LEVEL` | `INFO`, `WARNING`, `ERROR`, etc |
| `FORCE_HTTPS_HEADERS` | Habilita headers como HSTS |

## Sessão

| Variável | Uso |
|---|---|
| `SESSION_COOKIE_SAMESITE` | Política SameSite |
| `SESSION_COOKIE_SECURE` | Cookie apenas HTTPS (Use `1` em produção) |
| `PERMANENT_SESSION_LIFETIME_MINUTES` | Tempo de vida da sessão |

## Banco

A aplicação aceita `DATABASE_URL` ou variáveis separadas.

| Variável | Uso |
|---|---|
| `DATABASE_URL` | URL completa SQLAlchemy |
| `SQLSERVER_DRIVER` | Driver ODBC (Padrão: `ODBC Driver 17 for SQL Server`) |
| `SQLSERVER_HOST` | Host SQL Server |
| `SQLSERVER_PORT` | Porta, normalmente `1433` |
| `SQLSERVER_DATABASE` | Nome do banco |
| `SQLSERVER_USERNAME` | Usuário SQL |
| `SQLSERVER_PASSWORD` | Senha SQL |
| `SQLSERVER_TRUSTED_CONNECTION` | Autenticação integrada |
| `SQLSERVER_ENCRYPT` | Criptografia da conexão |
| `SQLSERVER_TRUST_SERVER_CERTIFICATE` | Aceitar certificado interno |
| `SQLSERVER_CONNECTION_TIMEOUT` | Timeout |
| `SQLSERVER_FAST_EXECUTEMANY` | Otimização pyodbc |
| `SQLALCHEMY_POOL_RECYCLE` | Reciclagem de conexões do pool |
| `SQLALCHEMY_ECHO` | Log de SQL (Evite em produção) |

## Microsoft Entra ID

| Variável | Uso |
|---|---|
| `AUTH_MICROSOFT_TENANT_ID` | Tenant ID |
| `AUTH_MICROSOFT_CLIENT_ID` | Client ID |
| `AUTH_MICROSOFT_CLIENT_SECRET` | Client secret |
| `AUTH_MICROSOFT_REDIRECT_URI` | Callback absoluto (Ex.: `http://localhost:5000/auth/callback`) |
| `AUTH_MICROSOFT_REDIRECT_PATH` | Caminho do callback (Padrão: `/auth/callback`) |
| `AUTH_MICROSOFT_SCOPES` | Scopes solicitados (Padrão: `User.Read`) |
| `AUTH_ALLOWED_EMAIL_DOMAINS` | Domínios permitidos |
| `AUTH_DEV_LOGIN_ENABLED` | Login local dev (Nunca em produção) |

## Notificações e e-mail corporativo

E-mail não deve usar SMTP. O envio corporativo deve sair pelo Brasif Gateway Microsoft Graph.

| Variável | Uso |
|---|---|
| `NOTIFICATIONS_EMAIL_ENABLED` | Liga envio de e-mail |
| `BRASIF_GATEWAY_BASE_URL` | Base URL do gateway (Padrão: `https://howard.brasif.local`) |
| `BRASIF_GATEWAY_API_KEY` | Chave enviada no header `x-api-key` |
| `BRASIF_GATEWAY_TIMEOUT_SECONDS` | Timeout do gateway |
| `BRASIF_GATEWAY_VERIFY_SSL` | Verificação SSL |
| `BRASIF_GATEWAY_MAX_RETRIES` | Tentativas extras para falhas transitórias, como 5xx/timeout |
| `BRASIF_GATEWAY_RETRY_BACKOFF_SECONDS` | Espera incremental entre tentativas transitórias |
| `MAIL_DEFAULT_SENDER` | Remetente opcional (Se vazio, o gateway usa a conta padrão do Vault) |
| `MAIL_MAX_RECIPIENTS` | Limite de destinatários por envio |
| `MAIL_MAX_BODY_LENGTH` | Limite de tamanho do corpo |
| `MAIL_MAX_ATTACHMENT_MB` | Limite por anexo |

Nunca registre `BRASIF_GATEWAY_API_KEY` em log, print, auditoria, traceback ou resposta ao usuário.

## Transferências

| Variável | Uso |
|---|---|
| `TRANSFER_EXPIRATION_DAYS` | Prazo padrão, em dias, para expirar transferências pendentes |

## Relatórios e exportações

| Variável | Uso |
|---|---|
| `REPORT_EXPORT_MAX_ROWS` | Limite máximo de linhas por exportação CSV/XLSX |

## Uploads

| Variável | Uso |
|---|---|
| `UPLOAD_BASE_DIR` | Pasta base de uploads (Se vazio, usa `instance/uploads`) |
| `APP_TRUST_PROXY_HEADERS` | Só habilite se houver proxy confiável ajustando `X-Forwarded-For` |
| `TOOL_REFERENCE_PHOTO_MAX_MB` | Tamanho máximo de foto da ferramenta |
| `INVENTORY_EVIDENCE_MAX_MB` | Tamanho máximo de evidência de inventário |
| `OCCURRENCE_ATTACHMENT_MAX_MB` | Tamanho máximo de anexos de ocorrência |
| `ALLOWED_IMAGE_EXTENSIONS` | Extensões de imagem |
| `ALLOWED_EVIDENCE_EXTENSIONS` | Extensões de evidência de inventário |
| `ALLOWED_OCCURRENCE_ATTACHMENT_EXTENSIONS` | Extensões de anexos de ocorrência |

## Exemplo mínimo local

```env
APP_ENV=development
SECRET_KEY=secret-key
AUTH_DEV_LOGIN_ENABLED=1
SQLSERVER_DRIVER=ODBC Driver 17 for SQL Server
SQLSERVER_HOST=localhost
SQLSERVER_DATABASE=ControleFerramentas
SQLSERVER_USERNAME=sa
SQLSERVER_PASSWORD=senha
SQLSERVER_TRUST_SERVER_CERTIFICATE=yes
```

## Exemplo mínimo produção

```env
APP_ENV=production
SECRET_KEY=<secret-key>
SESSION_COOKIE_SECURE=1
FORCE_HTTPS_HEADERS=1
AUTH_DEV_LOGIN_ENABLED=0
DATABASE_URL=<url-sql-server>
AUTH_MICROSOFT_TENANT_ID=<tenant>
AUTH_MICROSOFT_CLIENT_ID=<client>
AUTH_MICROSOFT_CLIENT_SECRET=<secret>
AUTH_MICROSOFT_REDIRECT_URI=https://controle-ferramentas.brasif.com/auth/callback
AUTH_MICROSOFT_REDIRECT_PATH=/auth/callback
AUTH_ALLOWED_EMAIL_DOMAINS=brasif.com.br,brasifagro.com.br
BRASIF_GATEWAY_BASE_URL=https://howard.brasif.local
BRASIF_GATEWAY_API_KEY=<api-key-do-gateway>
BRASIF_GATEWAY_MAX_RETRIES=2
BRASIF_GATEWAY_RETRY_BACKOFF_SECONDS=0.25
```