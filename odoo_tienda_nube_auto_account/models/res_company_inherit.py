from odoo import fields, models


class ResCompanyTnAutoAccount(models.Model):
    _inherit = "res.company"

    def _tn_auto_invoice_trigger_param_key(self):
        self.ensure_one()
        return "odoo_tienda_nube_auto_account.tn_auto_invoice_trigger_company_%s" % self.id

    tn_auto_invoice_trigger = fields.Selection(
        selection=[
            ("pick", "Al validar PICK"),
            ("out", "Al validar OUT"),
        ],
        string="Disparador Facturacion TN",
        compute="_compute_tn_auto_invoice_trigger",
        inverse="_inverse_tn_auto_invoice_trigger",
        help=(
            "Define cuando se dispara la facturacion automatica para ventas TN. "
            "Si se elige PICK y la ruta no tiene pickings internos, se usa OUT automaticamente."
        ),
    )

    def _compute_tn_auto_invoice_trigger(self):
        params = self.env["ir.config_parameter"].sudo()
        for company in self:
            value = params.get_param(company._tn_auto_invoice_trigger_param_key())
            company.tn_auto_invoice_trigger = value if value in ("pick", "out") else "out"

    def _inverse_tn_auto_invoice_trigger(self):
        params = self.env["ir.config_parameter"].sudo()
        for company in self:
            value = company.tn_auto_invoice_trigger if company.tn_auto_invoice_trigger in ("pick", "out") else "out"
            params.set_param(company._tn_auto_invoice_trigger_param_key(), value)
