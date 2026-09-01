"""link inventory divergence regularization actions

Revision ID: 202605210015
Revises: 202605190014
Create Date: 2026-05-21 00:00:15

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605210015"
down_revision = "202605190014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tb_cf_inventory_divergence",
        sa.Column("id_occurrence", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tb_cf_inventory_divergence",
        sa.Column("id_transfer", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_tb_cf_inv_div_occurrence",
        "tb_cf_inventory_divergence",
        "tb_cf_occurrence",
        ["id_occurrence"],
        ["id_occurrence"],
    )
    op.create_foreign_key(
        "fk_tb_cf_inv_div_transfer",
        "tb_cf_inventory_divergence",
        "tb_cf_transfer",
        ["id_transfer"],
        ["id_transfer"],
    )
    op.create_index(
        "ix_tb_cf_inventory_div_occurrence",
        "tb_cf_inventory_divergence",
        ["id_occurrence"],
    )
    op.create_index(
        "ix_tb_cf_inventory_div_transfer",
        "tb_cf_inventory_divergence",
        ["id_transfer"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tb_cf_inventory_div_transfer",
        table_name="tb_cf_inventory_divergence",
    )
    op.drop_index(
        "ix_tb_cf_inventory_div_occurrence",
        table_name="tb_cf_inventory_divergence",
    )
    op.drop_constraint(
        "fk_tb_cf_inv_div_transfer",
        "tb_cf_inventory_divergence",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_tb_cf_inv_div_occurrence",
        "tb_cf_inventory_divergence",
        type_="foreignkey",
    )
    op.drop_column("tb_cf_inventory_divergence", "id_transfer")
    op.drop_column("tb_cf_inventory_divergence", "id_occurrence")
