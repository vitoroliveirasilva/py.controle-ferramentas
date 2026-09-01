# Plano de produção

Este documento resume a preparação operacional para publicar o sistema.

## 1. Pré-requisitos

- SQL Server disponível.
- ODBC Driver instalado no host ou container.
- App Registration no Microsoft Entra ID com callback `/auth/callback`.
- Pasta persistente para uploads.
- Proxy reverso HTTPS.

## 2. Variáveis obrigatórias

```env
APP_ENV=production
SECRET_KEY=<secret-key>
SESSION_COOKIE_SECURE=1
FORCE_HTTPS_HEADERS=1
APP_TRUST_PROXY_HEADERS=1
AUTH_DEV_LOGIN_ENABLED=0
DATABASE_URL=<mssql+pyodbc-ou-variaveis-sqlserver>
AUTH_MICROSOFT_TENANT_ID=<tenant-id>
AUTH_MICROSOFT_CLIENT_ID=<client-id>
AUTH_MICROSOFT_CLIENT_SECRET=<client-secret>
AUTH_MICROSOFT_REDIRECT_URI=https://dominio/auth/callback
AUTH_MICROSOFT_REDIRECT_PATH=/auth/callback
AUTH_ALLOWED_EMAIL_DOMAINS=brasif.com.br
UPLOAD_BASE_DIR=<pasta-persistente>
BRASIF_GATEWAY_BASE_URL=https://howard.brasif.local
BRASIF_GATEWAY_API_KEY=<api-key>
BRASIF_GATEWAY_VERIFY_SSL=true
```

Use `APP_TRUST_PROXY_HEADERS=1` apenas se o proxy reverso for confiável e sanitizar headers de cliente.

## 3. Ordem de publicação

1. Congelar versão aprovada em homologação.
2. Executar `python scripts/quality_gate.py --include-docker`.
3. Validar `.env`/secrets no servidor.
4. Garantir permissão de escrita na pasta de uploads.
5. Aplicar migrations.
6. Rodar seed de permissões.
7. Criar ou revisar administrador global.
8. Subir aplicação.
9. Validar `/healthz` e `/readyz`.
10. Validar login Microsoft.
11. Executar checklist de fluxos críticos.
12. Registrar evidências da mudança.

## 4. Comandos de produção

```bash
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

## 5. Monitoramento mínimo

Monitorar:

- status HTTP de `/healthz`;
- status HTTP de `/readyz`;
- erros 401/403 incomuns;
- falhas de upload/download;
- falhas de gateway de e-mail;
- tempo de resposta dos relatórios;
- crescimento da pasta de uploads;
- auditorias de ações críticas.

## 6. Rollback

Rollback seguro:

1. Pausar a aplicação
2. Preservar logs recentes
3. Restaurar imagem/código anterior
4. Avaliar se houve migration aplicada
5. Validar `/healthz`, `/readyz`, login e fluxo de consulta

## 7. Pendências

- Rate limit para múltiplas instâncias.
- Exportações assíncronas para grandes volumes.
- Observabilidade centralizada com métricas e tracing.
- Testes end-to-end com navegador.
