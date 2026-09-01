# Revisão de segurança

## Controles implementados

- Autenticação Microsoft via MSAL
- Autorização local no banco
- Flask-Login para sessão
- CSRF em formulários
- Cookies seguros configuráveis
- Proteção contra open redirect
- Permissões no backend
- Escopos de acesso
- Auditoria em ações críticas
- Assinaturas internas
- Validação de uploads por extensão, tamanho, MIME e assinatura básica do arquivo
- Diretório de uploads fora de `static`
- Download de evidências por rotas autenticadas e autorizadas
- Sanitização de CSV/XLSX contra formula injection
- Auditoria de downloads e exportações sensíveis
- Tratamento de erros 401, 403, 404, 429 e 500
- `AUTH_DEV_LOGIN_ENABLED` bloqueado para produção
- `.env` ignorado no Git
- Configuração de e-mail direcionada ao Brasif Gateway Microsoft Graph, sem SMTP

## Pontos que exigem atenção em produção

- Garantir HTTPS
- Habilitar `SESSION_COOKIE_SECURE=1`
- Habilitar `FORCE_HTTPS_HEADERS=1`
- Usar `SECRET_KEY` forte
- Armazenar secrets em cofre/secret manager quando possível
- Restringir firewall do SQL Server
- Monitorar logs de erro e acesso negado
- Revisar permissões reais antes de liberar usuários
- Fazer backup de banco e uploads
- Garantir antivírus/varredura externa se anexos forem sensíveis

## Uploads

O sistema limita extensão, tamanho, MIME e assinatura básica do arquivo. Uma camada adicional de segurança em produção ainda é recomendada:

- antivírus corporativo;
- armazenamento segregado;
- permissões mínimas de leitura/escrita;
- não execução de arquivos enviados;
- logs de download quando necessário.

## Auditoria

Usuários comuns não devem alterar logs.

Eventos críticos devem registrar:

- usuário;
- ação;
- entidade;
- antes/depois;
- motivo;
- IP;
- user-agent;
- resultado.

## Assinaturas

A assinatura interna não substitui assinatura digital ICP-Brasil, portanto, ela representa apenas a evidência interna de confirmação/autorização dentro do sistema.

Nunca armazenar senha digitada, token, refresh token ou client secret em log, banco ou payload de assinatura.

## E-mail corporativo

O sistema não deve usar SMTP. O envio de e-mail deve ocorrer via Brasif Gateway Microsoft Graph, com `x-api-key` vindo de variável de ambiente ou cofre corporativo. A API key nunca deve ser logada, auditada em claro ou exibida ao usuário.

## Riscos residuais

- Sem MFA próprio no app, dependente da política Microsoft
- Sem antivírus interno para upload no MVP
- Sem WAF próprio no MVP
- Sem modo offline com reconciliação segura
- Escopos por filial/local dependem da qualidade dos vínculos cadastrais

## E-mail e Brasif Gateway

O sistema não deve usar SMTP. O client do Brasif Gateway Microsoft Graph deve:

- enviar `x-api-key` somente no header HTTP;
- nunca registrar API key, headers completos ou payload bruto na auditoria;
- validar assunto, corpo, destinatários, CC e anexos antes da chamada;
- aplicar retry apenas para timeout, 408, 429 e 5xx;
- nunca repetir envio em 401, 403 ou 422;
- registrar auditoria resumida com subject, contagem de destinatários, status, HTTP status, tentativa e duração;
- guardar histórico de entrega mascarando destinatários quando possível.

### Retries do gateway

Use `BRASIF_GATEWAY_MAX_RETRIES` com valor pequeno. Em produção, evite backoff agressivo para não gerar tempestade de requisições contra o gateway interno.
