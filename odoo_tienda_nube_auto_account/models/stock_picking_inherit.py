from odoo import models
from odoo.tools import float_compare


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

    def _tn_is_fully_reserved(self):
        """True si todos los movimientos pendientes tienen reservada la cantidad pedida."""
        self.ensure_one()
        moves = self.move_ids.filtered(lambda move: move.state not in ("done", "cancel"))
        if not moves:
            return False
        if "quantity" not in self.env["stock.move"]._fields:
            return self.state == "assigned"
        return all(
            float_compare(
                move.quantity, move.product_uom_qty, precision_rounding=move.product_uom.rounding
            )
            >= 0
            for move in moves
        )

    def _tn_try_auto_validate(self, force_without_stock=False):
        """Valida el remito para encadenar la facturacion automatica TN.

        button_validate completa con la demanda las cantidades que estan en cero, asi que
        sin chequear disponibilidad antes entregaria mercaderia que no esta y dejaria el
        stock en negativo. Por eso, salvo que la compañia pida lo contrario, solo se valida
        lo que esta completamente reservado.

        Devuelve True unicamente si el remito quedo en done: button_validate puede devolver
        una accion (un wizard) en vez de validar, con lo cual el valor de retorno no alcanza
        como confirmacion."""
        self.ensure_one()
        if self.state in ("done", "cancel"):
            return False
        if self.state == "draft":
            self.action_confirm()
        self.action_assign()

        if not force_without_stock and not self._tn_is_fully_reserved():
            return False

        # Marcamos los movimientos como pickeados, que es lo que hace el usuario en la
        # interfaz al cargar las cantidades; sin eso _action_done los puede dejar afuera.
        self.move_ids.filtered(lambda move: move.state not in ("done", "cancel")).picked = True

        # skip_backorder evita que _pre_action_done_hook devuelva el wizard de backorder en
        # vez de validar, y picking_ids_not_to_backorder evita que quede un remanente
        # pendiente cuando se valida sin stock completo.
        self.with_context(
            skip_backorder=True,
            picking_ids_not_to_backorder=self.ids,
            skip_sms=True,
        ).button_validate()

        return self.state == "done"

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
