# Configuração Microsoft Entra ID / Azure AD

## Objetivo

Configurar autenticação Microsoft para que o Entra ID autentique a identidade do usuário e o BD autorize o acesso.

## Criar App Registration

No portal Microsoft Entra:

1. Acesse **Microsoft Entra ID**.
2. Vá em **App registrations**.
3. Crie um novo registro.
4. Defina o nome, por exemplo: `Controle Ferramentas`.
5. Selecione o tipo de conta conforme política da empresa.
6. Cadastre uma Redirect URI do tipo **Web**.

Para desenvolvimento, use uma das opções abaixo e copie exatamente a mesma URL para o `.env`:

```text
http://localhost:5000/auth/callback
```

ou:

```text
http://127.0.0.1:5000/auth/callback
```

Para homologação/produção, use o domínio real HTTPS:

```text
https://controle-ferramentas.seudominio.com.br/auth/callback
```

## Criar segredo

1. Abra o App Registration.
2. Vá em **Certificates & secrets**.
3. Crie um **Client secret**.
4. Copie o valor do segredo.
5. Armazene somente no `.env`, secret manager ou cofre corporativo.

Nunca coloque segredo no código, README, commit, print ou chamado.

## Variáveis no `.env`

```env
AUTH_MICROSOFT_TENANT_ID=<tenant-id>
AUTH_MICROSOFT_CLIENT_ID=<client-id>
AUTH_MICROSOFT_CLIENT_SECRET=<client-secret>
AUTH_MICROSOFT_REDIRECT_URI=http://localhost:5000/auth/callback
AUTH_MICROSOFT_REDIRECT_PATH=/auth/callback
AUTH_MICROSOFT_SCOPES=User.Read
AUTH_ALLOWED_EMAIL_DOMAINS=brasif.com.br,brasifagro.com.br
```

Regras importantes:

- `AUTH_MICROSOFT_REDIRECT_URI` precisa ser uma URL absoluta `http` ou `https`.
- `AUTH_MICROSOFT_REDIRECT_PATH` precisa apontar para o mesmo caminho da URL absoluta.
- Se `AUTH_MICROSOFT_REDIRECT_URI` ficar vazio, o sistema monta a URL a partir da requisição atual. Em produção, prefira configurar a URL absoluta.
- Configuração Microsoft parcial é bloqueada. Defina tenant, client id e client secret juntos.

## Regra de autorização local

Mesmo autenticado na Microsoft, o usuário só entra se existir no BD e estiver:

- ativo;
- não bloqueado;
- não removido logicamente;
- compatível com o `microsoft_oid` vinculado, quando já existir vínculo.

Criar usuário:

```powershell
flask --app manage.py user-create --email usuario@brasif.com.br --name "Nome"
```

Dar perfil:

```powershell
flask --app manage.py user-grant-role --email usuario@brasif.com.br --role tecnico
```

Dar escopo:

```powershell
flask --app manage.py user-grant-scope --email usuario@brasif.com.br --scope-type proprio_usuario --scope-value usuario@brasif.com.br
```

## Login de desenvolvimento

Para teste local sem chamar a Microsoft:

```env
AUTH_DEV_LOGIN_ENABLED=1
```

Nunca habilite isso em produção. O app bloqueia `AUTH_DEV_LOGIN_ENABLED=1` quando `APP_ENV=production`.

## Erros comuns

### `redirect_uri_mismatch`

A URL do `.env` não bate exatamente com a cadastrada no App Registration.

Confira:

```env
AUTH_MICROSOFT_REDIRECT_URI=http://localhost:5000/auth/callback
AUTH_MICROSOFT_REDIRECT_PATH=/auth/callback
```

### Callback não encontrado

O endpoint canônico é:

```text
/auth/callback
```

Se houver callback legado cadastrado, como `/getAToken`, configure temporariamente:

```env
AUTH_MICROSOFT_REDIRECT_URI=http://localhost:5000/getAToken
AUTH_MICROSOFT_REDIRECT_PATH=/getAToken
```

Use isso apenas como transição. O padrão recomendado é migrar o App Registration para `/auth/callback`.

### Usuário autenticado mas acesso negado

O usuário existe na Microsoft, mas não foi cadastrado no banco local, está inativo, bloqueado, removido ou com e-mail/OID incompatível.

Verifique:

```powershell
flask --app manage.py access-list-user --email usuario@brasif.com.br
```

### Domínio não permitido

Confira:

```env
AUTH_ALLOWED_EMAIL_DOMAINS=brasif.com.br
```

Use lista separada por vírgulas quando necessário como por exemplo:

```env
AUTH_ALLOWED_EMAIL_DOMAINS=brasif.com.br,brasifagro.com.br
```