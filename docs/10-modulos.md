# Documentação dos módulos

## Auth

Responsável por login, logout, callback Microsoft, sessão e bloqueios de acesso.

Regra central:

```text
Microsoft autentica e BD autoriza.
```

## Users

Gerencia usuários locais, status ativo/bloqueado e vínculo Microsoft.

Comandos principais:

```powershell
flask --app manage.py user-create --email usuario@brasif.com.br --name "Usuário"
flask --app manage.py user-block --email usuario@brasif.com.br --reason "Motivo"
```

## Permissions

Gerencia perfis, permissões, vínculos e escopos.

Rotas:

- `/admin/access/`
- `/admin/access/me`

## Categories

Cadastro de categorias de ferramentas.

Permissão:

- `categories.manage`

## Locations

Cadastro de locais físicos/lógicos.

Permissão:

- `locations.manage`

## Tools

Cadastro de ferramentas, foto de referência, QR Code, etiqueta e consulta rápida.

Permissões:

- `tools.view`
- `tools.create`
- `tools.update`
- `tools.deactivate`
- `tools.critical_update`
- `tools.view_history`

## Custody

Controla custódia atual e linha do tempo.

Regras:

- uma única custódia atual por ferramenta;
- toda troca gera histórico;
- ferramenta baixada/inativa não recebe custódia comum.

## Transfers

Processo formal de transferência com origem, destino, itens e status.

Status principais:

- solicitada;
- aguardando confirmação da origem;
- aguardando confirmação do destino;
- concluída;
- recusada;
- cancelada;
- expirada.

## Inventories

Inventário compara esperado com encontrado.

Status:

- rascunho;
- em andamento;
- com divergência;
- aguardando assinatura;
- finalizado;
- cancelado.

## Divergences

Submódulo de inventário para pendências obrigatórias.

Divergência aberta bloqueia finalização.

## Occurrences

Registra perda, dano, baixa, manutenção, calibração, substituição e reintegração.

Pode alterar status da ferramenta quando aprovada.

## Signatures

Registra evidência de confirmação de ações críticas.

Campos relevantes:

- usuário;
- data/hora;
- ação;
- entidade;
- método;
- resultado;
- IP;
- user-agent;
- contexto.

## Reports

Central de relatórios e exportações CSV/Excel/print.

## Dashboard

Painel com indicadores operacionais e pendências.

## Notifications

Notificações internas e scanner sem Redis.

Comandos:

```powershell
flask --app manage.py notifications-scan
flask --app manage.py notifications-send-pending --dry-run
```

## Audit

Registra ações críticas e exportações sensíveis.
