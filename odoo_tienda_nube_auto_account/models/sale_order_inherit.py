import ast
import json
import logging

from datetime import date, datetime

from odoo import fields, models
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class SaleOrderTnAutoAccount(models.Model):
    _inherit = "sale.order"

    payment_status_tn = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("authorized", "Authorized"),
            ("paid", "Paid"),
            ("voided", "Voided"),
            ("refunded", "Refunded"),
        ],
        string="Payment Status TN",
        copy=False,
    )
    payment_method_tn = fields.Char(string="Payment Method TN", copy=False)
    gateway_tn = fields.Char(string="Gateway TN", copy=False)
    payment_date_tn = fields.Date(string="Payment Date TN", copy=False)
    payment_id_tn = fields.Char(string="Payment ID TN", copy=False)

    def create_order_from_tn(self):
        res = super().create_order_from_tn()
        for order in self:
            order._tn_refresh_payment_data_from_json()
            order._tn_try_auto_confirm_from_payment()
        return res

    def _tn_try_auto_confirm_from_payment(self):
        for order in self:
            if order.state != "draft" or not order.id_tn:
                continue
            if not order._tn_is_paid_or_authorized():
                continue
            try:
                order.action_confirm()
                order._tn_log(
                    level="success",
                    title="Orden confirmada automaticamente",
                    message="Orden confirmada por estado de pago TN (%s)." % (order.payment_status_tn or ""),
                )
            except Exception as err:
                order._tn_log(
                    level="error",
                    title="Error al confirmar orden automaticamente",
                    message=str(err),
                )

    def _tn_is_paid_or_authorized(self):
        self.ensure_one()
        return (self.payment_status_tn or "").lower() in ("paid", "authorized")

    def _tn_get_json_payload(self):
        self.ensure_one()
        payload = self.json_tn
        if not payload:
            return {}
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str):
            try:
                decoded = json.loads(payload)
                return decoded if isinstance(decoded, dict) else {}
            except Exception:
                try:
                    decoded = ast.literal_eval(payload)
                    return decoded if isinstance(decoded, dict) else {}
                except Exception:
                    _logger.debug("No se pudo parsear json_tn para la orden %s", self.id)
                    return {}
        return {}

    def _tn_parse_date(self, raw_date):
        if not raw_date:
            return False
        if isinstance(raw_date, datetime):
            return raw_date.date()
        if isinstance(raw_date, date):
            return raw_date
        if not isinstance(raw_date, str):
            return False

        value = raw_date.strip()
        if not value:
            return False

        try:
            return fields.Date.to_date(value[:10])
        except Exception:
            return False

    def _tn_extract_payment_data(self, order_data):
        status = (order_data.get("payment_status") or order_data.get("financial_status") or "").lower()
        method = order_data.get("payment_method") or order_data.get("payment_method_name") or ""
        gateway = order_data.get("gateway") or order_data.get("gateway_name") or ""
        payment_id = str(order_data.get("payment_id") or "")
        payment_date = (
            order_data.get("payment_date")
            or order_data.get("paid_at")
            or order_data.get("processed_at")
            or False
        )

        payments = order_data.get("payments") or order_data.get("payment_details") or []
        if isinstance(payments, dict):
            payments = [payments]
        if payments and isinstance(payments[0], dict):
            first_payment = payments[0]
            status = (
                status
                or (first_payment.get("status") or first_payment.get("payment_status") or "").lower()
            )
            method = (
                method
                or first_payment.get("payment_method")
                or first_payment.get("method")
                or first_payment.get("name")
                or ""
            )
            gateway = gateway or first_payment.get("gateway") or first_payment.get("gateway_name") or ""
            payment_id = payment_id or str(
                first_payment.get("id")
                or first_payment.get("payment_id")
                or first_payment.get("transaction_id")
                or ""
            )
            payment_date = payment_date or first_payment.get("paid_at") or first_payment.get("date") or first_payment.get("created_at")

        transactions = order_data.get("transactions") or []
        if isinstance(transactions, dict):
            transactions = [transactions]
        if transactions and isinstance(transactions[0], dict):
            first_tx = transactions[0]
            status = status or (first_tx.get("status") or "").lower()
            gateway = gateway or first_tx.get("gateway") or ""
            payment_id = payment_id or str(first_tx.get("id") or first_tx.get("transaction_id") or "")
            payment_date = payment_date or first_tx.get("created_at")

        if status not in ("pending", "authorized", "paid", "voided", "refunded"):
            status = "pending" if status else False

        return {
            "payment_status_tn": status,
            "payment_method_tn": method or False,
            "gateway_tn": gateway or False,
            "payment_date_tn": self._tn_parse_date(payment_date),
            "payment_id_tn": payment_id or False,
        }

    def _tn_refresh_payment_data_from_json(self):
        for order in self:
            payload = order._tn_get_json_payload()
            if not payload:
                continue
            values = order._tn_extract_payment_data(payload)
            order.write(values)

    def _tn_get_payment_mapping(self):
        self.ensure_one()
        method = (self.payment_method_tn or "").strip()
        if not method:
            return False

        Mapping = self.env["tn.payment.method.mapping"].sudo().with_company(self.company_id)
        gateway = (self.gateway_tn or "").strip()

        mapping = False
        if gateway:
            mapping = Mapping.search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("payment_method_tn", "=", method),
                    ("gateway_tn", "=", gateway),
                    ("active", "=", True),
                ],
                limit=1,
            )

        if not mapping:
            mapping = Mapping.search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("payment_method_tn", "=", method),
                    ("gateway_tn", "=", ""),
                    ("active", "=", True),
                ],
                limit=1,
            )

        return mapping

    def _tn_create_invoice_if_needed(self):
        self.ensure_one()

        invoices = self.invoice_ids.filtered(lambda move: move.move_type == "out_invoice" and move.state != "cancel")
        if invoices:
            invoice = invoices.sorted(lambda mv: (mv.invoice_date or fields.Date.today(), mv.id), reverse=True)[:1]
            return invoice

        created_invoices = self._create_invoices(final=True)
        invoice = created_invoices.filtered(lambda move: move.move_type == "out_invoice")[:1] if created_invoices else False
        if not invoice:
            invoices = self.invoice_ids.filtered(lambda move: move.move_type == "out_invoice" and move.state != "cancel")
            invoice = invoices[:1] if invoices else False

        if invoice:
            if invoice.state == "draft":
                invoice.action_post()
            self._tn_log(
                level="success",
                title="Factura creada automaticamente",
                message="Factura %s creada/publicada para la orden %s." % (invoice.name or invoice.id, self.name),
            )

        return invoice

    def _tn_payment_ref(self):
        self.ensure_one()
        order_ref = self.number_tn or self.id_tn or self.name
        payment_ref = self.payment_id_tn or "SIN_PAYMENT_ID"
        return "TN %s / %s" % (order_ref, payment_ref)

    def _tn_find_existing_payment(self, invoice, journal, ref):
        self.ensure_one()
        candidates = self.env["account.payment"].search(
            [
                ("state", "=", "posted"),
                ("partner_id", "=", invoice.partner_id.id),
                ("journal_id", "=", journal.id),
                ("payment_type", "=", "inbound"),
                ("ref", "=", ref),
            ]
        )
        for payment in candidates:
            if float_is_zero(
                payment.amount - invoice.amount_residual,
                precision_rounding=invoice.currency_id.rounding,
            ):
                return payment
        return False

    def _tn_create_payment_for_invoice(self, invoice):
        self.ensure_one()

        if not invoice or invoice.state != "posted":
            return False

        if float_is_zero(invoice.amount_residual, precision_rounding=invoice.currency_id.rounding):
            return False

        mapping = self._tn_get_payment_mapping()
        if not mapping:
            self._tn_log(
                level="warning",
                title="No hay mapeo para metodo de pago TN",
                message=(
                    "No se encontro mapeo para metodo '%s' y gateway '%s'. "
                    "La factura %s se creo sin pago automatico."
                )
                % (self.payment_method_tn or "", self.gateway_tn or "", invoice.name or invoice.id),
            )
            return False

        journal = mapping.journal_id
        payment_method_line = journal.inbound_payment_method_line_ids[:1]
        if not payment_method_line:
            self._tn_log(
                level="error",
                title="Diario sin metodo de pago inbound",
                message="El diario %s no tiene lineas de metodo de pago inbound." % journal.name,
            )
            return False

        ref = self._tn_payment_ref()
        existing_payment = self._tn_find_existing_payment(invoice, journal, ref)
        if existing_payment:
            return existing_payment

        payment_vals = {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": invoice.partner_id.id,
            "amount": invoice.amount_residual,
            "currency_id": invoice.currency_id.id,
            "date": self.payment_date_tn or fields.Date.context_today(self),
            "journal_id": journal.id,
            "payment_method_line_id": payment_method_line.id,
            "ref": ref,
            "company_id": self.company_id.id,
        }

        payment = self.env["account.payment"].create(payment_vals)
        payment.action_post()

        self._tn_log(
            level="success",
            title="Pago creado automaticamente",
            message="Pago %s creado para factura %s en diario %s." % (payment.name, invoice.name or invoice.id, journal.name),
        )

        return payment

    def _tn_reconcile_payment_invoice(self, payment, invoice):
        self.ensure_one()
        if not payment or not invoice:
            return False

        try:
            invoice_lines = invoice.line_ids.filtered(
                lambda line: line.account_id.account_type == "asset_receivable" and not line.reconciled
            )
            payment_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_id.account_type == "asset_receivable" and not line.reconciled
            )

            for account in invoice_lines.mapped("account_id"):
                lines_to_reconcile = (invoice_lines + payment_lines).filtered(lambda line: line.account_id == account)
                if lines_to_reconcile:
                    lines_to_reconcile.reconcile()

            self._tn_log(
                level="success",
                title="Conciliacion automatica exitosa",
                message="Factura %s conciliada con pago %s." % (invoice.name or invoice.id, payment.name),
            )
            return True
        except Exception as err:
            self._tn_log(
                level="error",
                title="Error en conciliacion automatica",
                message="No se pudo conciliar factura %s con pago %s." % (invoice.name or invoice.id, payment.name),
                error_tn=str(err),
            )
            return False

    def _tn_run_auto_billing_and_payment(self):
        for order in self:
            if not order.id_tn:
                continue

            if not order._tn_is_paid_or_authorized():
                order._tn_log(
                    level="warning",
                    title="Orden TN no pagada",
                    message="Se omite facturacion automatica porque el estado de pago TN es '%s'." % (order.payment_status_tn or ""),
                )
                continue

            invoice = order._tn_create_invoice_if_needed()
            if not invoice:
                order._tn_log(
                    level="warning",
                    title="No se pudo crear factura automatica",
                    message="No se genero factura para la orden %s." % (order.name),
                )
                continue

            payment = order._tn_create_payment_for_invoice(invoice)
            if payment:
                order._tn_reconcile_payment_invoice(payment, invoice)

    def _tn_log(self, level, title, message, error_tn=False):
        self.ensure_one()
        self.env["tn.log"].sudo().create_log(
            name=title,
            message=message,
            model="sale.order",
            model_id=self.id,
            level=level,
            error_tn=error_tn,
        )
