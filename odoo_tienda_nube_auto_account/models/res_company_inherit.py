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

    tn_auto_validate_picking = fields.Boolean(
        string="Validar remito automaticamente",
        help=(
            "Al confirmarse una orden de Tienda Nube, valida automaticamente el remito que "
            "dispara la facturacion (PICK u OUT segun el disparador de arriba) y, en rutas de "
            "varios pasos, toda la cadena. Al validarse se encadenan factura, pago y "
            "conciliacion. Solo se valida si Tienda Nube informa el pago como paid o authorized."
        ),
    )

    tn_auto_validate_without_stock = fields.Boolean(
        string="Validar aunque no haya stock",
        help=(
            "Si esta desactivado, el remito no se valida cuando los movimientos no estan "
            "completamente reservados: la entrega queda pendiente y se avisa en la venta para "
            "que la resuelva una persona. Si se activa, se valida igual y el stock puede quedar "
            "en negativo."
        ),
    )

    tn_invoice_journal_id = fields.Many2one(
        "account.journal",
        string="Diario de Facturacion TN",
        domain="[('type', '=', 'sale'), ('company_id', '=', id)]",
        help="Si se configura, las facturas automaticas TN se crean con este diario.",
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
