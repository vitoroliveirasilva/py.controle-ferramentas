# Matriz de permissões

## Conceitos

O sistema usa:

- RBAC para perfis;
- permissões granulares para ações;
- escopos para limitar a área de atuação;
- validação obrigatória no backend.

Toda ação sensível deve usar decorator ou validação equivalente no service e não ocultar botão em template.

## Perfis iniciais

| Código | Nome | Uso esperado |
|---|---|---|
| `admin_sistema` | Administrador do sistema | Acesso total à configuração, operação e auditoria |
| `gestor` | Gestor | Gestão por filial, equipe ou local |
| `responsavel_local` | Responsável por oficina/site | Operação do próprio local |
| `tecnico` | Técnico | Acesso às próprias ferramentas, inventários e pendências |
| `auditor_interno` | Auditor interno | Consulta histórica, auditoria e relatórios |
| `contabilidade_patrimonial` | Contabilidade/Cadastro patrimonial | Consulta e decisão em eventos patrimoniais |
| `consulta_gerencial` | Consulta gerencial | Dashboard e relatórios por escopo |

## Escopos

| Escopo | Exemplo | Finalidade |
|---|---|---|
| `global` | `*` | Acesso global |
| `filial` | `Jundiai` | Limita por filial |
| `local` | `Almoxarifado Central` | Limita por local |
| `tecnico` | `12345` | Limita por técnico/matrícula |
| `proprio_usuario` | `email@brasif.com.br` | Limita ao próprio usuário |
| `departamento` | `Oficina` | Limita por departamento |

## Matriz atual

| Grupo | Permissão | Nome | admin_sistema | gestor | responsavel_local | tecnico | auditor_interno | contabilidade_patrimonial | consulta_gerencial |
|---|---|---|---|---|---|---|---|---|---|
| Usuários | users.view | Visualizar usuários | &#10003; | &#10003; |  |  | &#10003; |  |  |
| Usuários | users.create | Criar usuários | &#10003; | &#10003; |  |  |  |  |  |
| Usuários | users.update | Atualizar usuários | &#10003; | &#10003; |  |  |  |  |  |
| Usuários | users.disable | Inativar usuários | &#10003; |  |  |  |  |  |  |
| Acessos | roles.view | Visualizar perfis | &#10003; | &#10003; |  |  | &#10003; |  |  |
| Acessos | roles.manage | Gerenciar perfis | &#10003; |  |  |  |  |  |  |
| Acessos | permissions.manage | Gerenciar permissões | &#10003; |  |  |  |  |  |  |
| Ferramentas | tools.view | Visualizar ferramentas | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; |
| Ferramentas | tools.create | Criar ferramentas | &#10003; | &#10003; |  |  |  |  |  |
| Ferramentas | tools.update | Atualizar ferramentas | &#10003; | &#10003; |  |  |  |  |  |
| Ferramentas | tools.deactivate | Inativar ferramentas | &#10003; | &#10003; |  |  |  |  |  |
| Ferramentas | tools.critical_update | Alterar campos críticos | &#10003; | &#10003; |  |  |  |  |  |
| Ferramentas | tools.view_history | Ver histórico | &#10003; | &#10003; | &#10003; |  | &#10003; | &#10003; |  |
| Cadastros | categories.manage | Gerenciar categorias | &#10003; | &#10003; |  |  |  |  |  |
| Cadastros | locations.manage | Gerenciar locais | &#10003; | &#10003; |  |  |  |  |  |
| Custódia | custody.view | Visualizar custódia | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; |
| Custódia | custody.assign_initial | Atribuir custódia inicial | &#10003; | &#10003; | &#10003; |  |  |  |  |
| Custódia | custody.view_history | Ver histórico de custódia | &#10003; | &#10003; | &#10003; |  | &#10003; | &#10003; |  |
| Custódia | custody.force_change | Alterar custódia administrativamente | &#10003; |  |  |  |  |  |  |
| Transferências | transfers.view | Visualizar transferências | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; |  | &#10003; |
| Transferências | transfers.create | Criar transferências | &#10003; | &#10003; | &#10003; | &#10003; |  |  |  |
| Transferências | transfers.confirm_origin | Confirmar origem | &#10003; | &#10003; | &#10003; |  |  |  |  |
| Transferências | transfers.confirm_destination | Confirmar destino | &#10003; | &#10003; | &#10003; | &#10003; |  |  |  |
| Transferências | transfers.cancel | Cancelar transferências | &#10003; | &#10003; | &#10003; |  |  |  |  |
| Transferências | transfers.refuse | Recusar transferências | &#10003; | &#10003; | &#10003; | &#10003; |  |  |  |
| Transferências | transfers.force_cancel | Forçar cancelamento | &#10003; |  |  |  |  |  |  |
| Transferências | transfers.override | Sobrescrever fluxo de transferência | &#10003; |  |  |  |  |  |  |
| Inventários | inventories.view | Visualizar inventários | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; |  | &#10003; |
| Inventários | inventories.create | Criar inventários | &#10003; | &#10003; | &#10003; |  |  |  |  |
| Inventários | inventories.update | Atualizar inventários | &#10003; | &#10003; | &#10003; |  |  |  |  |
| Inventários | inventories.perform | Executar inventários | &#10003; | &#10003; | &#10003; | &#10003; |  |  |  |
| Inventários | inventories.resolve_divergence | Regularizar divergências | &#10003; | &#10003; | &#10003; |  |  |  |  |
| Inventários | inventories.finish | Finalizar inventários | &#10003; | &#10003; | &#10003; |  |  |  |  |
| Inventários | inventories.cancel | Cancelar inventários | &#10003; | &#10003; |  |  |  |  |  |
| Inventários | inventories.sign | Assinar inventários | &#10003; | &#10003; | &#10003; |  |  |  |  |
| Ocorrências | occurrences.view | Visualizar ocorrências | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; |
| Ocorrências | occurrences.create | Criar ocorrências | &#10003; | &#10003; | &#10003; | &#10003; |  |  |  |
| Ocorrências | occurrences.approve | Aprovar ocorrências | &#10003; | &#10003; |  |  |  | &#10003; |  |
| Ocorrências | occurrences.reject | Recusar ocorrências | &#10003; | &#10003; |  |  |  | &#10003; |  |
| Ocorrências | occurrences.resolve | Resolver ocorrências | &#10003; | &#10003; | &#10003; |  |  |  |  |
| Assinaturas | signatures.create | Criar assinaturas | &#10003; | &#10003; | &#10003; | &#10003; |  |  |  |
| Auditoria | audit.view | Visualizar auditoria | &#10003; | &#10003; |  |  | &#10003; |  |  |
| Relatórios | reports.view | Visualizar relatórios | &#10003; | &#10003; | &#10003; |  | &#10003; | &#10003; | &#10003; |
| Relatórios | reports.export | Exportar relatórios | &#10003; |  |  |  | &#10003; | &#10003; |  |
| Dashboard | dashboard.view | Visualizar dashboard | &#10003; | &#10003; | &#10003; |  | &#10003; | &#10003; | &#10003; |
| Notificações | notifications.view | Visualizar notificações | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; | &#10003; |
| Notificações | notifications.manage | Gerenciar notificações | &#10003; | &#10003; |  |  |  |  |  |

## Comandos úteis

```powershell
flask --app manage.py access-seed
flask --app manage.py access-list-roles
flask --app manage.py access-list-user --email usuario@brasif.com.br
flask --app manage.py user-grant-role --email usuario@brasif.com.br --role tecnico
flask --app manage.py user-grant-scope --email usuario@brasif.com.br --scope-type proprio_usuario --scope-value usuario@brasif.com.br
```

## Regras de revisão

- Revise perfis antes de homologação
- Evite dar `admin_sistema` para usuários operacionais
- Use `global:*` somente para administradores e papéis realmente corporativos
- Prefira escopos por filial/local/técnico quando possível
