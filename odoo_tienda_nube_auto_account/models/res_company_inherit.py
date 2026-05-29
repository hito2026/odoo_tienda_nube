from odoo import fields, models


class ResCompanyTnAutoAccount(models.Model):
    _inherit = "res.company"

    tn_auto_invoice_trigger = fields.Selection(
        selection=[
            ("pick", "Al validar PICK"),
            ("out", "Al validar OUT"),
        ],
        string="Disparador Facturacion TN",
        default="out",
        help=(
            "Define cuando se dispara la facturacion automatica para ventas TN. "
            "Si se elige PICK y la ruta no tiene pickings internos, se usa OUT automaticamente."
        ),
    )
