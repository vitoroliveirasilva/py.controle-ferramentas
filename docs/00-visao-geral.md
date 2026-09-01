# Visão geral

## Objetivo

O Sistema de Controle de Ferramentas é uma aplicação web corporativa para governança operacional e patrimonial de ferramentas. Ele permite controlar cadastro, posse atual, histórico, inventários, divergências, transferências, ocorrências, assinaturas internas, relatórios e notificações.

## Problemas que o sistema resolve

- Falta de visão em tempo real sobre ferramentas por técnico, local ou filial.
- Fragilidade de histórico quando documentos antigos são apagados ou mantidos fora do sistema.
- Dificuldade para saber quem está com cada ferramenta e desde quando.
- Dificuldade para auditar perdas, danos, baixas, substituições e divergências.
- Ausência de fluxo formal para aceite de transferência.
- Ausência de bloqueio operacional para inventário com pendência aberta.

## Stack

- Python
- Flask
- Flask App Factory
- Flask-Login
- Flask-WTF
- SQLAlchemy 2.x
- Flask-Migrate/Alembic
- SQL Server via pyodbc
- Microsoft Entra ID/Azure AD via MSAL
- Jinja2
- Bootstrap 5
- Pytest
- Ruff
- Docker e Docker Compose
- GitHub Actions CI

## Arquitetura resumida

A aplicação é organizada por módulos funcionais:

```text
app/
  auth/
  users/
  permissions/
  categories/
  locations/
  tools/
  custody/
  transfers/
  inventories/
  occurrences/
  signatures/
  reports/
  dashboard/
  notifications/
  audit/
  core/
  db/
```

Cada módulo concentra rotas, services, repositories, forms, models e templates quando aplicável.

## Fluxo central

1. O usuário autentica pela Microsoft.
2. O sistema procura o usuário local pelo e-mail/OID.
3. O acesso só é liberado se o usuário local estiver ativo, desbloqueado e com permissões.
4. Perfis e escopos determinam o que o usuário pode acessar.
5. Ferramentas são cadastradas e recebem custódia.
6. Transferências mudam custódia via processo formal.
7. Inventários conferem o esperado contra o encontrado.
8. Divergências travam finalização enquanto não forem regularizadas.
9. Ocorrências registram perda, dano, baixa, manutenção, calibração e eventos patrimoniais.
10. Ações críticas geram auditoria e assinatura interna.
11. Relatórios, dashboard e notificações dão visão operacional e gerencial.

## Limites assumidos no MVP

- Sem Redis.
- Sem Celery.
- Sem app mobile nativo.
- Sem modo offline.
- Sem integração automática com ERP/RH.
- Sem OCR e leitura massiva por scanner.
- Sem BI avançado externo.
