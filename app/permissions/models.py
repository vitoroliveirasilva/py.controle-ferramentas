from __future__ import annotations

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin


class RoleModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_role"
    __table_args__ = (
        Index("ux_tb_cf_role_codigo", "codigo", unique=True),
        Index("ix_tb_cf_role_ativo", "ativo"),
        {"comment": "Perfis de acesso do Sistema de Controle de Ferramentas."},
    )

    id_role: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(80), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    permissions: Mapped[list[RolePermissionModel]] = relationship(
        "RolePermissionModel",
        back_populates="role",
        cascade="all, delete-orphan",
    )
    users: Mapped[list[UserRoleModel]] = relationship(
        "UserRoleModel",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class PermissionModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_permission"
    __table_args__ = (
        Index("ux_tb_cf_permission_codigo", "codigo", unique=True),
        Index("ix_tb_cf_permission_grupo", "grupo"),
        Index("ix_tb_cf_permission_ativo", "ativo"),
        {"comment": "Permissões granulares validadas no backend."},
    )

    id_permission: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    codigo: Mapped[str] = mapped_column(String(120), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    grupo: Mapped[str] = mapped_column(String(80), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    roles: Mapped[list[RolePermissionModel]] = relationship(
        "RolePermissionModel",
        back_populates="permission",
        cascade="all, delete-orphan",
    )


class RolePermissionModel(TimestampMixin, BaseModel):

    __tablename__ = "tb_cf_role_permission"
    __table_args__ = (
        UniqueConstraint("id_role", "id_permission", name="uq_tb_cf_role_permission"),
        Index("ix_tb_cf_role_permission_role", "id_role"),
        Index("ix_tb_cf_role_permission_permission", "id_permission"),
        {"comment": "Vínculo N:N entre perfis e permissões."},
    )

    id_role_permission: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_role: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_role.id_role", ondelete="CASCADE"),
        nullable=False,
    )
    id_permission: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_permission.id_permission", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[RoleModel] = relationship("RoleModel", back_populates="permissions")
    permission: Mapped[PermissionModel] = relationship(
        "PermissionModel", back_populates="roles"
    )


class UserRoleModel(TimestampMixin, BaseModel):

    __tablename__ = "tb_cf_user_role"
    __table_args__ = (
        UniqueConstraint("id_usuario", "id_role", name="uq_tb_cf_user_role"),
        Index("ix_tb_cf_user_role_usuario", "id_usuario"),
        Index("ix_tb_cf_user_role_role", "id_role"),
        {"comment": "Vínculo N:N entre usuários locais e perfis."},
    )

    id_user_role: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    id_role: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_role.id_role", ondelete="CASCADE"),
        nullable=False,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    role: Mapped[RoleModel] = relationship("RoleModel", back_populates="users")


class UserScopeModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_user_scope"
    __table_args__ = (
        UniqueConstraint(
            "id_usuario",
            "tipo_escopo",
            "valor_escopo",
            name="uq_tb_cf_user_scope_valor",
        ),
        Index("ix_tb_cf_user_scope_usuario", "id_usuario"),
        Index("ix_tb_cf_user_scope_tipo_valor", "tipo_escopo", "valor_escopo"),
        {"comment": "Escopos de acesso por usuário para limitar dados por contexto."},
    )

    id_user_scope: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_escopo: Mapped[str] = mapped_column(String(40), nullable=False)
    valor_escopo: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        server_default=text("'*'"),
    )
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
