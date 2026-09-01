from __future__ import annotations

from enum import StrEnum


# Enum base para status de registros.
# Usa comportamento de string para facilitar formulários, JSON e filtros.
class BaseStrEnum(StrEnum):
    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(item.value, item.label) for item in cls]

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()


class RecordStatus(BaseStrEnum):
    ACTIVE = "ativo"
    INACTIVE = "inativo"


class ScopeType(BaseStrEnum):
    GLOBAL = "global"
    FILIAL = "filial"
    LOCAL = "local"
    TECNICO = "tecnico"
    PROPRIO_USUARIO = "proprio_usuario"
    DEPARTAMENTO = "departamento"


class LocationType(BaseStrEnum):
    TECNICO = "tecnico"
    OFICINA = "oficina"
    SITE_CLIENTE = "site_cliente"
    ALMOXARIFADO = "almoxarifado"
    DEPARTAMENTO = "departamento"
    MANUTENCAO_CALIBRACAO = "manutencao_calibracao"


class ToolStatus(BaseStrEnum):
    DISPONIVEL = "disponivel"
    EM_USO = "em_uso"
    DANIFICADA = "danificada"
    MANUTENCAO = "manutencao"
    CALIBRACAO = "calibracao"
    TRANSFERENCIA = "transferencia"
    INVENTARIO = "inventario"
    BAIXADA = "baixada"
    INATIVA = "inativa"


class ToolCriticality(BaseStrEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    PATRIMONIAL = "patrimonial"


class CustodyType(BaseStrEnum):
    TECNICO = "tecnico"
    OFICINA = "oficina"
    SITE_CLIENTE = "site_cliente"
    ALMOXARIFADO = "almoxarifado"
    DEPARTAMENTO = "departamento"
    MANUTENCAO_CALIBRACAO = "manutencao_calibracao"


class ToolTimelineEventType(BaseStrEnum):
    CUSTODIA_INICIAL = "custodia_inicial"
    CUSTODIA_TRANSFERIDA = "custodia_transferida"
    CUSTODIA_ENCERRADA = "custodia_encerrada"
    TRANSFERENCIA_SOLICITADA = "transferencia_solicitada"
    TRANSFERENCIA_CONCLUIDA = "transferencia_concluida"
    TRANSFERENCIA_RECUSADA = "transferencia_recusada"
    TRANSFERENCIA_CANCELADA = "transferencia_cancelada"
    INVENTARIO_ABERTO = "inventario_aberto"
    INVENTARIO_ITEM_CONFERIDO = "inventario_item_conferido"
    INVENTARIO_CANCELADO = "inventario_cancelado"
    INVENTARIO_DIVERGENCIA_ABERTA = "inventario_divergencia_aberta"
    INVENTARIO_DIVERGENCIA_REGULARIZADA = "inventario_divergencia_regularizada"
    INVENTARIO_AGUARDANDO_ASSINATURA = "inventario_aguardando_assinatura"
    INVENTARIO_FINALIZADO = "inventario_finalizado"
    ASSINATURA_REGISTRADA = "assinatura_registrada"
    OCORRENCIA_ABERTA = "ocorrencia_aberta"
    OCORRENCIA_APROVADA = "ocorrencia_aprovada"
    OCORRENCIA_RECUSADA = "ocorrencia_recusada"
    OCORRENCIA_RESOLVIDA = "ocorrencia_resolvida"
    REFERENCIA_FOTO_ATUALIZADA = "referencia_foto_atualizada"
    REFERENCIA_FOTO_REMOVIDA = "referencia_foto_removida"
    INVENTARIO_EVIDENCIA_ADICIONADA = "inventario_evidencia_adicionada"
    INVENTARIO_ITEM_LIDO_POR_CODIGO = "inventario_item_lido_por_codigo"


class TransferStatus(BaseStrEnum):
    SOLICITADA = "solicitada"
    AGUARDANDO_ORIGEM = "aguardando_confirmacao_origem"
    AGUARDANDO_DESTINO = "aguardando_confirmacao_destino"
    CONCLUIDA = "concluida"
    RECUSADA = "recusada"
    CANCELADA = "cancelada"
    EXPIRADA = "expirada"


class TransferItemStatus(BaseStrEnum):
    PENDENTE = "pendente"
    AGUARDANDO_DESTINO = "aguardando_destino"
    CONCLUIDO = "concluido"
    RECUSADO = "recusado"
    CANCELADO = "cancelado"
    EXPIRADO = "expirado"


class TransferType(BaseStrEnum):
    TECNICO_PARA_TECNICO = "tecnico_para_tecnico"
    TECNICO_PARA_OFICINA = "tecnico_para_oficina"
    OFICINA_PARA_TECNICO = "oficina_para_tecnico"
    OFICINA_PARA_SITE = "oficina_para_site"
    SITE_PARA_OFICINA = "site_para_oficina"
    ALMOXARIFADO_PARA_TECNICO = "almoxarifado_para_tecnico"
    MANUTENCAO_PARA_ORIGEM = "manutencao_para_origem"
    TEMPORARIA = "temporaria"
    DEFINITIVA = "definitiva"
    EM_LOTE = "em_lote"


class InventoryType(BaseStrEnum):
    FERIAS = "ferias"
    RESCISAO = "rescisao"
    OFICINA = "oficina"
    SITE = "site"
    ANUAL = "anual"
    EXTRAORDINARIO = "extraordinario"


class InventoryStatus(BaseStrEnum):
    RASCUNHO = "rascunho"
    EM_ANDAMENTO = "em_andamento"
    COM_DIVERGENCIA = "com_divergencia"
    AGUARDANDO_ASSINATURA = "aguardando_assinatura"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"


class InventoryItemStatus(BaseStrEnum):
    PENDENTE = "pendente"
    ENCONTRADO = "encontrado"
    FALTANTE = "faltante"
    EXCEDENTE = "excedente"
    DANIFICADO = "danificado"
    SUBSTITUIDO = "substituido"
    NAO_APLICAVEL = "nao_aplicavel"
    REGULARIZADO = "regularizado"


class InventoryScopeType(BaseStrEnum):
    TECNICO = "tecnico"
    LOCAL = "local"


class InventoryDivergenceType(BaseStrEnum):
    FERRAMENTA_FALTANTE = "ferramenta_faltante"
    FERRAMENTA_EXCEDENTE = "ferramenta_excedente"
    FERRAMENTA_DANIFICADA = "ferramenta_danificada"
    CODIGO_DIVERGENTE = "codigo_divergente"
    ATIVO_IMOBILIZADO_DIVERGENTE = "ativo_imobilizado_divergente"
    SUBSTITUICAO_NAO_REGISTRADA = "substituicao_nao_registrada"
    FERRAMENTA_BAIXADA_ENCONTRADA = "ferramenta_baixada_encontrada"
    TRANSFERENCIA_PENDENTE = "transferencia_pendente"
    CUSTODIA_INCONSISTENTE = "custodia_inconsistente"


class InventoryDivergenceStatus(BaseStrEnum):
    ABERTA = "aberta"
    REGULARIZADA = "regularizada"
    JUSTIFICADA = "justificada"
    CANCELADA = "cancelada"


class InventoryDivergenceAction(BaseStrEnum):
    RECONTAR = "recontar"
    JUSTIFICAR_COM_APROVACAO = "justificar_com_aprovacao"
    ABRIR_OCORRENCIA = "abrir_ocorrencia"
    TRANSFERIR = "transferir"
    CADASTRAR_ITEM_EXCEDENTE = "cadastrar_item_excedente"
    VINCULAR_RESPONSAVEL_CORRETO = "vincular_responsavel_correto"
    BAIXAR_POR_PERDA = "baixar_por_perda"
    REGISTRAR_DANO = "registrar_dano"
    REGISTRAR_SUBSTITUICAO = "registrar_substituicao"
    REINTEGRAR_FERRAMENTA = "reintegrar_ferramenta"
    CANCELAR_PROCESSO_COM_MOTIVO = "cancelar_processo_com_motivo"


class OccurrenceType(BaseStrEnum):
    PERDA = "perda"
    EXTRAVIO = "extravio"
    DANO = "dano"
    SUBSTITUICAO = "substituicao"
    BAIXA = "baixa"
    MANUTENCAO = "manutencao"
    CALIBRACAO = "calibracao"
    REINTEGRACAO = "reintegracao"
    REGULARIZACAO_CADASTRAL = "regularizacao_cadastral"


class OccurrenceStatus(BaseStrEnum):
    ABERTA = "aberta"
    EM_ANALISE = "em_analise"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    APROVADA = "aprovada"
    RECUSADA = "recusada"
    RESOLVIDA = "resolvida"
    CANCELADA = "cancelada"


class OccurrenceDecision(BaseStrEnum):
    APROVAR = "aprovar"
    RECUSAR = "recusar"
    RESOLVER = "resolver"
    CANCELAR = "cancelar"


class SignatureAction(BaseStrEnum):
    INVENTORY_SIGN = "inventories.sign"
    INVENTORY_CANCEL = "inventories.cancel.sign"
    INVENTORY_DIVERGENCE_RESOLVE = "inventories.divergence.resolve.sign"
    TRANSFER_CONFIRM_ORIGIN = "transfers.confirm_origin.sign"
    TRANSFER_CONFIRM_DESTINATION = "transfers.confirm_destination.sign"
    TRANSFER_REFUSE = "transfers.refuse.sign"
    TRANSFER_CANCEL = "transfers.cancel.sign"
    OCCURRENCE_APPROVE = "occurrences.approve.sign"
    OCCURRENCE_REJECT = "occurrences.reject.sign"
    OCCURRENCE_RESOLVE = "occurrences.resolve.sign"
    OCCURRENCE_CANCEL = "occurrences.cancel.sign"


class SignatureMethod(BaseStrEnum):
    SESSAO_AUTENTICADA = "sessao_autenticada"


class SignatureResult(BaseStrEnum):
    CONFIRMADO = "confirmado"
    APROVADO = "aprovado"
    RECUSADO = "recusado"
    CANCELADO = "cancelado"
    RESOLVIDO = "resolvido"
    REGULARIZADO = "regularizado"


class NotificationType(BaseStrEnum):
    INVENTARIO_VENCIDO = "inventario_vencido"
    TRANSFERENCIA_PENDENTE = "transferencia_pendente"
    ASSINATURA_PENDENTE = "assinatura_pendente"
    DIVERGENCIA_CRITICA = "divergencia_critica"
    OCORRENCIA_CRITICA = "ocorrencia_critica"
    SISTEMA = "sistema"


class NotificationPriority(BaseStrEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class NotificationStatus(BaseStrEnum):
    PENDENTE = "pendente"
    LIDA = "lida"
    ENVIADA = "enviada"
    FALHA = "falha"
    CANCELADA = "cancelada"


class NotificationChannel(BaseStrEnum):
    INTERNA = "interna"
    EMAIL = "email"
