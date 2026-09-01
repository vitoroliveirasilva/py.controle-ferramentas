from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional

from app.models.enums import (
    InventoryDivergenceAction,
    InventoryItemStatus,
    InventoryScopeType,
    InventoryStatus,
    InventoryType,
)


class InventoryForm(FlaskForm):
    titulo = StringField(
        "Título",
        validators=[DataRequired(), Length(min=3, max=180)],
        description="Ex.: Inventário anual da oficina Jundiaí.",
    )
    tipo_inventario = SelectField(
        "Tipo de inventário",
        choices=InventoryType.choices(),
        validators=[DataRequired()],
    )
    escopo_tipo = SelectField(
        "Escopo",
        choices=InventoryScopeType.choices(),
        validators=[DataRequired()],
    )
    escopo_usuario_id = SelectField("Técnico", coerce=int, validators=[Optional()])
    escopo_location_id = SelectField("Local", coerce=int, validators=[Optional()])
    status_inicial = SelectField(
        "Status inicial",
        choices=[
            (InventoryStatus.RASCUNHO.value, "Rascunho"),
            (InventoryStatus.EM_ANDAMENTO.value, "Em andamento"),
        ],
        validators=[DataRequired()],
    )
    descricao = TextAreaField(
        "Descrição/observações", validators=[Optional(), Length(max=2000)]
    )
    submit = SubmitField("Abrir inventário")


class InventoryItemUpdateForm(FlaskForm):
    item_status = SelectField(
        "Resultado da conferência",
        choices=InventoryItemStatus.choices(),
        validators=[DataRequired()],
    )
    observacao = TextAreaField("Observação", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Salvar conferência")


class InventoryQuickStatusForm(FlaskForm):
    item_status = HiddenField("Status", validators=[DataRequired()])
    observacao = HiddenField("Observação", validators=[Optional()])


class InventoryDivergenceResolveForm(FlaskForm):
    acao_regularizacao = SelectField(
        "Ação de regularização",
        choices=InventoryDivergenceAction.choices(),
        validators=[DataRequired()],
    )
    occurrence_id = IntegerField(
        "Ocorrência vinculada",
        validators=[Optional()],
        description="Obrigatório quando a divergência já tiver uma ocorrência aberta.",
    )
    transfer_id = IntegerField(
        "Transferência vinculada",
        validators=[Optional()],
        description="Obrigatório para regularização por transferência já aberta.",
    )
    resolucao = TextAreaField(
        "Justificativa/descrição da regularização",
        validators=[DataRequired(), Length(min=5, max=4000)],
    )
    submit = SubmitField("Regularizar divergência")


class InventoryExcessForm(FlaskForm):
    identificador = StringField(
        "Código, ativo ou série encontrado",
        validators=[DataRequired(), Length(max=120)],
    )
    observacao = TextAreaField(
        "Observação",
        validators=[DataRequired(), Length(min=5, max=2000)],
    )
    submit = SubmitField("Registrar excedente")


class InventoryFinishForm(FlaskForm):
    motivo = TextAreaField(
        "Observação de fechamento",
        validators=[Optional(), Length(max=2000)],
    )
    submit = SubmitField("Enviar para assinatura")


class InventoryCancelForm(FlaskForm):
    motivo = TextAreaField(
        "Motivo", validators=[DataRequired(), Length(min=5, max=2000)]
    )
    submit = SubmitField("Cancelar inventário")


class InventoryScanForm(FlaskForm):
    codigo = StringField(
        "Código lido",
        validators=[DataRequired(), Length(max=120)],
        description="Leia o QR Code/código de barras ou digite código interno, ativo ou série.",
    )
    observacao = StringField("Observação", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Marcar como encontrado")


class InventoryEvidenceUploadForm(FlaskForm):
    evidencia = FileField("Foto/anexo de evidência")
    observacao = StringField("Observação", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Enviar evidência")
