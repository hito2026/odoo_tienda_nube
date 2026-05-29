from odoo import api, fields, models


class TnPaymentMethodMapping(models.Model):
    _name = "tn.payment.method.mapping"
    _description = "Mapeo Metodo de Pago TN"
    _rec_name = "display_name"

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
        store=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compania",
        required=True,
        default=lambda self: self.env.company,
    )
    payment_method_tn = fields.Char(string="Metodo de Pago TN", required=True)
    gateway_tn = fields.Char(string="Gateway TN", default="")
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario",
        required=False,
        domain="[('type', 'in', ['bank', 'cash']), ('company_id', '=', company_id)]",
        help="Puede dejarse vacio inicialmente. El pago automatico se habilita al asignar un diario.",
    )

    _sql_constraints = [
        (
            "tn_payment_method_mapping_unique",
            "unique(company_id, payment_method_tn, gateway_tn)",
            "Ya existe un mapeo para este metodo y gateway en la compania.",
        )
    ]

    @api.depends("payment_method_tn", "gateway_tn", "journal_id")
    def _compute_display_name(self):
        for rec in self:
            method = rec.payment_method_tn or ""
            gateway = rec.gateway_tn or "*"
            journal = rec.journal_id.name or "PENDIENTE"
            rec.display_name = f"{method} / {gateway} -> {journal}"
