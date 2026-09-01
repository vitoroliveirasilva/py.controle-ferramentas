from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    name: str
    group: str
    description: str


@dataclass(frozen=True)
class RoleDefinition:
    code: str
    name: str
    description: str
    permissions: tuple[str, ...]


PERMISSIONS: tuple[PermissionDefinition, ...] = tuple(
    PermissionDefinition(code, name, group, description)
    for code, name, group, description in (
        (
            "users.view",
            "Visualizar usuários",
            "Usuários",
            "Consulta usuários locais.",
        ),
        (
            "users.create",
            "Criar usuários",
            "Usuários",
            "Cadastra usuários locais.",
        ),
        (
            "users.update",
            "Atualizar usuários",
            "Usuários",
            "Atualiza usuários locais.",
        ),
        (
            "users.disable",
            "Inativar usuários",
            "Usuários",
            "Bloqueia ou inativa usuários.",
        ),
        (
            "roles.view",
            "Visualizar perfis",
            "Acessos",
            "Consulta perfis e vínculos.",
        ),
        (
            "roles.manage",
            "Gerenciar perfis",
            "Acessos",
            "Administra perfis.",
        ),
        (
            "permissions.manage",
            "Gerenciar permissões",
            "Acessos",
            "Administra matriz de acesso.",
        ),
        (
            "tools.view",
            "Visualizar ferramentas",
            "Ferramentas",
            "Consulta ferramentas.",
        ),
        (
            "tools.create",
            "Criar ferramentas",
            "Ferramentas",
            "Cadastra ferramentas.",
        ),
        (
            "tools.update",
            "Atualizar ferramentas",
            "Ferramentas",
            "Atualiza ferramentas.",
        ),
        (
            "tools.deactivate",
            "Inativar ferramentas",
            "Ferramentas",
            "Inativa ferramentas.",
        ),
        (
            "tools.critical_update",
            "Alterar campos críticos",
            "Ferramentas",
            "Altera campos críticos.",
        ),
        (
            "tools.view_history",
            "Ver histórico",
            "Ferramentas",
            "Consulta histórico da ferramenta.",
        ),
        (
            "categories.manage",
            "Gerenciar categorias",
            "Cadastros",
            "Administra categorias.",
        ),
        (
            "locations.manage",
            "Gerenciar locais",
            "Cadastros",
            "Administra locais.",
        ),
        (
            "custody.view",
            "Visualizar custódia",
            "Custódia",
            "Consulta custódia atual.",
        ),
        (
            "custody.assign_initial",
            "Atribuir custódia inicial",
            "Custódia",
            "Define custódia inicial.",
        ),
        (
            "custody.view_history",
            "Ver histórico de custódia",
            "Custódia",
            "Consulta linha do tempo.",
        ),
        (
            "custody.force_change",
            "Alterar custódia administrativamente",
            "Custódia",
            "Corrige custódia fora do fluxo padrão com justificativa e auditoria.",
        ),
        (
            "transfers.view",
            "Visualizar transferências",
            "Transferências",
            "Consulta transferências.",
        ),
        (
            "transfers.create",
            "Criar transferências",
            "Transferências",
            "Solicita transferências.",
        ),
        (
            "transfers.confirm_origin",
            "Confirmar origem",
            "Transferências",
            "Confirma saída.",
        ),
        (
            "transfers.confirm_destination",
            "Confirmar destino",
            "Transferências",
            "Confirma recebimento.",
        ),
        (
            "transfers.cancel",
            "Cancelar transferências",
            "Transferências",
            "Cancela transferências.",
        ),
        (
            "transfers.refuse",
            "Recusar transferências",
            "Transferências",
            "Recusa transferências.",
        ),
        (
            "transfers.force_cancel",
            "Forçar cancelamento",
            "Transferências",
            "Cancela como admin.",
        ),
        (
            "transfers.override",
            "Sobrescrever fluxo de transferência",
            "Transferências",
            "Permite confirmação/cancelamento administrativo com auditoria.",
        ),
        (
            "inventories.view",
            "Visualizar inventários",
            "Inventários",
            "Consulta inventários.",
        ),
        (
            "inventories.create",
            "Criar inventários",
            "Inventários",
            "Abre inventários.",
        ),
        (
            "inventories.update",
            "Atualizar inventários",
            "Inventários",
            "Atualiza inventários.",
        ),
        (
            "inventories.perform",
            "Executar inventários",
            "Inventários",
            "Realiza conferência.",
        ),
        (
            "inventories.resolve_divergence",
            "Regularizar divergências",
            "Inventários",
            "Regulariza divergências.",
        ),
        (
            "inventories.finish",
            "Finalizar inventários",
            "Inventários",
            "Finaliza inventários.",
        ),
        (
            "inventories.cancel",
            "Cancelar inventários",
            "Inventários",
            "Cancela inventários.",
        ),
        (
            "inventories.sign",
            "Assinar inventários",
            "Inventários",
            "Assina inventários.",
        ),
        (
            "occurrences.view",
            "Visualizar ocorrências",
            "Ocorrências",
            "Consulta ocorrências.",
        ),
        (
            "occurrences.create",
            "Criar ocorrências",
            "Ocorrências",
            "Registra ocorrências.",
        ),
        (
            "occurrences.approve",
            "Aprovar ocorrências",
            "Ocorrências",
            "Aprova ocorrências.",
        ),
        (
            "occurrences.reject",
            "Recusar ocorrências",
            "Ocorrências",
            "Recusa ocorrências.",
        ),
        (
            "occurrences.resolve",
            "Resolver ocorrências",
            "Ocorrências",
            "Encerra ocorrências.",
        ),
        (
            "signatures.create",
            "Criar assinaturas",
            "Assinaturas",
            "Assina ações críticas.",
        ),
        (
            "audit.view",
            "Visualizar auditoria",
            "Auditoria",
            "Consulta auditoria.",
        ),
        (
            "reports.view",
            "Visualizar relatórios",
            "Relatórios",
            "Consulta relatórios.",
        ),
        (
            "reports.export",
            "Exportar relatórios",
            "Relatórios",
            "Exporta relatórios.",
        ),
        (
            "dashboard.view",
            "Visualizar dashboard",
            "Dashboard",
            "Acessa indicadores.",
        ),
        (
            "notifications.view",
            "Visualizar notificações",
            "Notificações",
            "Consulta notificações.",
        ),
        (
            "notifications.manage",
            "Gerenciar notificações",
            "Notificações",
            "Configura notificações.",
        ),
    )
)

ALL_PERMISSION_CODES = tuple(permission.code for permission in PERMISSIONS)
OPERATIONAL_PERMISSION_CODES = tuple(
    code
    for code in ALL_PERMISSION_CODES
    if code
    not in {
        "permissions.manage",
        "roles.manage",
        "users.disable",
        "reports.export",
        "custody.force_change",
        "transfers.force_cancel",
        "transfers.override",
    }
)
READ_ONLY_PERMISSION_CODES = tuple(
    code
    for code in ALL_PERMISSION_CODES
    if code.endswith(".view")
    or code
    in {
        "tools.view_history",
        "custody.view_history",
        "dashboard.view",
    }
)

ROLE_DEFINITIONS: tuple[RoleDefinition, ...] = (
    RoleDefinition(
        "admin_sistema",
        "Administrador do sistema",
        "Acesso total para configuração, operação e auditoria.",
        ALL_PERMISSION_CODES,
    ),
    RoleDefinition(
        "gestor",
        "Gestor",
        "Gestão operacional por escopo de filial, equipe ou local.",
        OPERATIONAL_PERMISSION_CODES,
    ),
    RoleDefinition(
        "responsavel_local",
        "Responsável por oficina/site",
        "Operação de inventários, custódia e transferências do próprio local.",
        (
            "tools.view",
            "tools.view_history",
            "custody.view",
            "custody.assign_initial",
            "custody.view_history",
            "transfers.view",
            "transfers.create",
            "transfers.confirm_origin",
            "transfers.confirm_destination",
            "transfers.cancel",
            "transfers.refuse",
            "inventories.view",
            "inventories.create",
            "inventories.update",
            "inventories.perform",
            "inventories.resolve_divergence",
            "inventories.finish",
            "inventories.sign",
            "occurrences.view",
            "occurrences.create",
            "occurrences.resolve",
            "signatures.create",
            "reports.view",
            "dashboard.view",
            "notifications.view",
        ),
    ),
    RoleDefinition(
        "tecnico",
        "Técnico",
        "Acesso operacional às próprias ferramentas, inventários e pendências.",
        (
            "tools.view",
            "custody.view",
            "transfers.view",
            "transfers.create",
            "transfers.confirm_destination",
            "transfers.refuse",
            "inventories.view",
            "inventories.perform",
            "occurrences.view",
            "occurrences.create",
            "signatures.create",
            "notifications.view",
        ),
    ),
    RoleDefinition(
        "auditor_interno",
        "Auditor interno",
        "Consulta histórica e auditoria sem operação comum.",
        READ_ONLY_PERMISSION_CODES + ("audit.view", "reports.export"),
    ),
    RoleDefinition(
        "contabilidade_patrimonial",
        "Contabilidade/Cadastro patrimonial",
        "Consulta e análise de eventos patrimoniais, baixas e ativos.",
        (
            "tools.view",
            "tools.view_history",
            "custody.view",
            "custody.view_history",
            "occurrences.view",
            "occurrences.approve",
            "occurrences.reject",
            "reports.view",
            "reports.export",
            "dashboard.view",
            "notifications.view",
        ),
    ),
    RoleDefinition(
        "consulta_gerencial",
        "Consulta gerencial",
        "Consulta de dashboard e relatórios por escopo.",
        (
            "tools.view",
            "custody.view",
            "transfers.view",
            "inventories.view",
            "occurrences.view",
            "reports.view",
            "dashboard.view",
            "notifications.view",
        ),
    ),
)
