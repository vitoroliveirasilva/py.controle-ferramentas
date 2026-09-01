# Deploy e operação

## Modelo recomendado

- Aplicação Flask via Gunicorn
- Proxy reverso HTTPS, como Nginx/IIS/Apache
- SQL Server corporativo
- Variáveis de ambiente configuradas fora do código
- Uploads em volume persistente
- Logs coletados por plataforma do servidor
- CI aprovado antes da publicação

## Variáveis obrigatórias em produção

```env
APP_ENV=production
SECRET_KEY=<secret-key>
SESSION_COOKIE_SECURE=1
FORCE_HTTPS_HEADERS=1
APP_TRUST_PROXY_HEADERS=1
AUTH_DEV_LOGIN_ENABLED=0
DATABASE_URL=<url-sql-server>
AUTH_MICROSOFT_TENANT_ID=<tenant-id>
AUTH_MICROSOFT_CLIENT_ID=<client-id>
AUTH_MICROSOFT_CLIENT_SECRET=<client-secret>
AUTH_MICROSOFT_REDIRECT_URI=https://dominio/auth/callback
AUTH_MICROSOFT_REDIRECT_PATH=/auth/callback
AUTH_ALLOWED_EMAIL_DOMAINS=brasif.com.br
BRASIF_GATEWAY_BASE_URL=https://howard.brasif.local
BRASIF_GATEWAY_API_KEY=<api-key-do-gateway>
BRASIF_GATEWAY_TIMEOUT_SECONDS=10
BRASIF_GATEWAY_VERIFY_SSL=true
BRASIF_GATEWAY_MAX_RETRIES=2
BRASIF_GATEWAY_RETRY_BACKOFF_SECONDS=0.25
UPLOAD_BASE_DIR=<pasta-persistente>
REPORT_EXPORT_MAX_ROWS=500
TRANSFER_EXPIRATION_DAYS=7
```

Use `APP_TRUST_PROXY_HEADERS=1` somente atrás de proxy confiável.

## Ordem de deploy

1. Publicar código aprovado no CI
2. Instalar dependências
3. Configurar `.env`/secrets
4. Garantir pasta persistente de uploads
5. Rodar migrations
6. Rodar seed de permissões
7. Criar/validar administrador
8. Subir serviço
9. Testar health/readiness
10. Testar login Microsoft
11. Testar relatórios, uploads e escopos
12. Executar checklist de homologação final

## Comandos

```bash
pip install -r requirements.txt
python scripts/quality_gate.py
flask --app manage.py db upgrade
flask --app manage.py access-seed
flask --app manage.py db-ping
gunicorn --bind 0.0.0.0:8000 wsgi:application
```

Com Docker:

```bash
docker compose build
docker compose up -d
docker compose exec web flask --app manage.py db upgrade
docker compose exec web flask --app manage.py access-seed
docker compose exec web flask --app manage.py db-ping
```

## Health checks

- `/healthz`: aplicação viva
- `/readyz`: dependências principais prontas

O `/readyz` pode responder `503` durante instalação incompleta. O corpo indica o motivo.

## Rotinas agendadas

Sem Redis/Celery no MVP. Use scheduler externo para comandos CLI:

```bash
flask --app manage.py notifications-scan
flask --app manage.py notifications-send-pending --dry-run
flask --app manage.py notifications-send-pending
```

Recomendações:

- rode `notifications-scan` em janela definida pela operação;
- teste envio com `--dry-run` antes de habilitar e-mail real;
- monitore falhas do Brasif Gateway.

## Backup

Realize backup regular de:

- banco SQL Server;
- pasta de uploads;
- configuração segura das variáveis de ambiente;
- evidências de auditoria exigidas pela operação.

## Rollback

Para rollback seguro:

1. Pause a aplicação
2. Preserve logs recentes
3. Restaure versão anterior do código/imagem
4. Avalie se migration precisa de downgrade
5. Restaure backup se houve alteração estrutural destrutiva
6. Suba aplicação
7. Valide health, login e consulta de ferramentas

Evite migrations destrutivas em produção sem janela de manutenção.

## Segurança operacional

- Nunca habilite `AUTH_DEV_LOGIN_ENABLED` em produção
- Não exponha stack trace
- Não versione `.env`
- Use HTTPS
- Revogue secrets expostos
- Restrinja acesso ao SQL Server
- Revise permissões de upload
- Não configure SMTP. O envio de e-mail deve usar o Brasif Gateway Microsoft Graph
- Rode `flask --app manage.py access-seed` após novas permissões
