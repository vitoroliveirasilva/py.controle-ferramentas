# Homologação final

Este checklist consolida a validação mínima antes de liberar o Controle de Ferramentas em produção.

## 1. Catraca técnica

Execute no Windows PowerShell:

```powershell
python scripts/quality_gate.py
```

Para incluir build Docker:

```powershell
python scripts/quality_gate.py --include-docker
```

Comandos equivalentes, caso prefira rodar etapa por etapa:

```powershell
ruff check .
python -m compileall -q app tests scripts
python -m pytest -q
docker compose build
```

## 2. Banco e migrations

Em homologação com SQL Server:

```powershell
flask --app manage.py db current
flask --app manage.py db upgrade
flask --app manage.py access-seed
flask --app manage.py db-ping
```

Validar manualmente:

- existe apenas uma head de migration;
- a migration `202605210015` foi aplicada;
- tabelas `tb_cf_*` existem no banco correto;
- permissões novas aparecem no cadastro de acesso;
- nenhum dado produtivo foi apagado.

## 3. Autenticação Microsoft

Validar:

- `AUTH_MICROSOFT_REDIRECT_URI` termina em `/auth/callback`;
- o mesmo callback está cadastrado no Microsoft Entra ID;
- usuário autenticado pela Microsoft, mas inexistente no banco, não acessa;
- usuário inativo, bloqueado ou removido logicamente não acessa;
- login dev está desativado em produção;
- logout encerra sessão.

## 4. RBAC e ABAC

Criar pelo menos três usuários de homologação:

- admin global;
- responsável por um local específico;
- técnico sem escopo global.

Validar:

- admin vê tudo;
- responsável por local só vê ferramentas, inventários, ocorrências e relatórios do seu escopo;
- técnico só vê itens sob sua custódia ou pendências relacionadas;
- acesso direto por URL fora do escopo retorna bloqueio;
- exportações respeitam o mesmo escopo da tela.

## 5. Ferramentas e custódia

Validar:

- criação de ferramenta com código interno único;
- ativo imobilizado único quando preenchido;
- foto de referência aceita apenas formatos permitidos;
- ferramenta ativa possui custódia atual;
- não é possível ter duas custódias atuais para a mesma ferramenta;
- baixa/perda/extravio/substituição encerra custódia;
- troca administrativa exige `custody.force_change` e motivo forte.

## 6. Transferências

Validar:

- criação de transferência com origem, destino, motivo e itens;
- ferramenta com transferência pendente não entra em outra transferência aberta;
- origem só confirma quando o ator tem relação com a origem ou `transfers.override`;
- destino só confirma quando o ator tem relação com o destino ou `transfers.override`;
- transferência concluída não pode ser cancelada;
- expiração restaura o status operacional esperado;
- todo fluxo gera auditoria/linha do tempo.

## 7. Inventários e divergências

Validar:

- inventário carrega lista esperada por local/técnico;
- leitura de ferramenta esperada marca como encontrada;
- ferramenta cadastrada, mas não esperada, entra como excedente;
- faltante/danificado/excedente gera divergência;
- inventário com divergência aberta não finaliza;
- regularização exige justificativa e ação real;
- ações críticas vinculam ocorrência ou transferência quando aplicável;
- evidências respeitam upload seguro.

## 8. Ocorrências

Validar:

- abertura de perda, extravio, dano, substituição, baixa e reintegração;
- anexo aceita apenas extensão, MIME e assinatura permitidos;
- aprovação altera status da ferramenta quando aplicável;
- reintegração sem custódia válida é bloqueada;
- anexos só baixam por usuário autenticado e autorizado.

## 9. Relatórios e exportações

Validar:

- relatórios respeitam escopo;
- filtros da tela são aplicados na exportação;
- exportação acima de `REPORT_EXPORT_MAX_ROWS` é bloqueada;
- CSV/XLSX neutraliza valores iniciados por `=`, `+`, `-` e `@`;
- exportação sensível gera auditoria.

## 10. Notificações e e-mail

Validar primeiro em simulação:

```powershell
flask --app manage.py notifications-scan
flask --app manage.py notifications-send-pending --dry-run
```

Depois, se `NOTIFICATIONS_EMAIL_ENABLED=1`:

- gateway configurado com `BRASIF_GATEWAY_API_KEY`;
- nenhum SMTP configurado;
- erro 422 não gera retry;
- timeout/5xx gera retry controlado;
- histórico mascara destinatários;
- auditoria não grava API key, headers completos ou corpo sensível.

## 11. Docker

Validar:

```powershell
docker compose build
docker compose up -d
docker compose ps
docker compose exec web flask --app manage.py db-ping
docker compose exec web flask --app manage.py access-seed
```

Acessar:

- `/healthz` deve retornar `200`;
- `/readyz` deve retornar `200` ou `503` com motivo claro enquanto dependência faltar.

## 12. Evidências de homologação

Guardar evidências de:

- execução de testes;
- build Docker;
- migrations aplicadas;
- login Microsoft;
- isolamento de escopo;
- transferência concluída;
- inventário finalizado sem pendência;
- divergência regularizada com ação;
- exportação sanitizada;
- envio simulado e envio real pelo gateway, quando habilitado;
- auditoria.
