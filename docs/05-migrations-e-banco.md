# Migrations e banco de dados

## Banco alvo

O banco alvo do projeto é SQL Server.

O projeto usa:

- SQLAlchemy 2.x
- Flask-SQLAlchemy
- Flask-Migrate
- Alembic
- pyodbc

## Comandos principais

Ver conexão:

```powershell
flask --app manage.py db-info
flask --app manage.py db-ping
```

Aplicar migrations:

```powershell
flask --app manage.py db upgrade
```

Ver revision atual:

```powershell
flask --app manage.py db current
```

Criar nova migration:

```powershell
flask --app manage.py db migrate -m "Descrição da migração"
```

Reverter última migration:

```powershell
flask --app manage.py db downgrade
```

## Importante

Não rode:

```powershell
flask db init
```

O diretório `migrations/` já está versionado.

## Tabelas principais

- `tb_cf_usuario`
- `tb_cf_role`
- `tb_cf_permission`
- `tb_cf_role_permission`
- `tb_cf_user_role`
- `tb_cf_user_scope`
- `tb_cf_tool_category`
- `tb_cf_location`
- `tb_cf_tool`
- `tb_cf_tool_custody`
- `tb_cf_tool_timeline_event`
- `tb_cf_transfer`
- `tb_cf_transfer_item`
- `tb_cf_inventory`
- `tb_cf_inventory_item`
- `tb_cf_inventory_divergence`
- `tb_cf_occurrence`
- `tb_cf_occurrence_attachment`
- `tb_cf_internal_signature`
- `tb_cf_audit_log`
- `tb_cf_notification`
- `tb_cf_notification_delivery`

## Booleans no SQL Server

Para campos `BIT`, evite:

```python
Model.campo.is_(True)
Model.campo.is_(False)
```

Isso pode gerar SQL inválido no SQL Server, como `IS 1` e `IS 0`.

Use:

```python
from sqlalchemy import true, false

Model.campo == true()
Model.campo == false()
```

## Exclusão física

Dados operacionais e históricos devem usar inativação, baixa ou soft delete sempre que aplicável.

Não apague histórico de:

- ferramentas;
- custódias;
- inventários;
- divergências;
- transferências;
- ocorrências;
- assinaturas;
- auditoria.

## Transações

Ações críticas devem ocorrer em services transacionais, principalmente:

- troca de custódia;
- confirmação de transferência;
- finalização de inventário;
- regularização de divergência;
- aprovação de ocorrência;
- baixa patrimonial.
