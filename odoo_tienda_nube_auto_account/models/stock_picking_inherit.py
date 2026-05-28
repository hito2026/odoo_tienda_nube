from odoo import models


class StockPickingTnAutoAccount(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        result = super().button_validate()

        for picking in self:
            if picking.state != "done":
                continue
            if picking.picking_type_id.code != "outgoing":
                continue
            if not picking.sale_id:
                continue

            order = picking.sale_id
            if not order.id_tn:
                continue

            pending_out_pickings = order.picking_ids.filtered(
                lambda current: current.picking_type_id.code == "outgoing"
                and current.state not in ("done", "cancel")
            )
            if pending_out_pickings:
                continue

            order._tn_run_auto_billing_and_payment()

        return result
