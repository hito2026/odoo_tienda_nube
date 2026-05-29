from odoo import models


class StockPickingTnAutoAccount(models.Model):
    _inherit = "stock.picking"

    def _tn_should_trigger_auto_flow(self, order):
        self.ensure_one()

        mode = order.company_id.tn_auto_invoice_trigger or "out"
        is_outgoing = self.picking_type_id.code == "outgoing"
        is_internal = self.picking_type_id.code == "internal"

        if mode == "out":
            if not is_outgoing:
                return False
            pending_out_pickings = order.picking_ids.filtered(
                lambda current: current.picking_type_id.code == "outgoing"
                and current.state not in ("done", "cancel")
            )
            return not pending_out_pickings

        internal_pickings = order.picking_ids.filtered(
            lambda current: current.picking_type_id.code == "internal"
            and current.state != "cancel"
        )
        if internal_pickings:
            if not is_internal:
                return False
            pending_internal_pickings = internal_pickings.filtered(
                lambda current: current.state not in ("done", "cancel")
            )
            return not pending_internal_pickings

        if not is_outgoing:
            return False

        pending_out_pickings = order.picking_ids.filtered(
            lambda current: current.picking_type_id.code == "outgoing"
            and current.state not in ("done", "cancel")
        )
        return not pending_out_pickings

    def button_validate(self):
        result = super().button_validate()

        for picking in self:
            if picking.state != "done":
                continue
            if not picking.sale_id:
                continue

            order = picking.sale_id
            if not order.id_tn:
                continue

            if not picking._tn_should_trigger_auto_flow(order):
                continue

            order._tn_run_auto_billing_and_payment()

        return result
