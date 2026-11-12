# -*- coding: utf-8 -*-
import base64
import logging
import traceback
from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

LABEL_STATUS = [
    ('STARTED', 'Solicitada'),
    ('IN_PROGRESS', 'En proceso'),
    ('READY_TO_DOWNLOAD', 'Preparando documento'),
    ('READY_TO_USE', 'Lista'),
    ('DOWNLOADED', 'Descargada'),
    ('SUSPENDED', 'Suspendida'),
    ('FAILED', 'Fallida'),
    ('CANCELED', 'Cancelada'),
]
# Tienda Nube permite descargar el documento en estos estados
LABEL_READY = ('READY_TO_USE', 'DOWNLOADED')
# Etiquetas que ya no sirven: el fulfillment order admite pedir otra
LABEL_DEAD = ('FAILED', 'CANCELED')
# El carrier todavía la está generando (pasan solas a FAILED a los 30 min)
LABEL_PENDING = ('STARTED', 'IN_PROGRESS', 'READY_TO_DOWNLOAD')
# Fulfillment orders a los que no tiene sentido pedirles etiqueta
FO_CLOSED = ('DELIVERED', 'CANCELED', 'CANCELLED')


class TnShippingLabel(models.Model):
    _name = 'tn.shipping.label'
    _description = 'Etiqueta de envío Tienda Nube'
    _order = 'create_date desc'
    _rec_name = 'label_id'

    _label_id_uniq = models.Constraint('unique(label_id)', 'La etiqueta de Tienda Nube ya está registrada.')

    sale_order_id = fields.Many2one('sale.order', 'Orden de venta', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='sale_order_id.company_id', store=True)
    fulfillment_order_id = fields.Char('Fulfillment Order TN', required=True)
    label_id = fields.Char('ID etiqueta TN', required=True, index=True)
    status = fields.Selection(LABEL_STATUS, string='Estado', default='STARTED')
    tracking_code = fields.Char('Código de seguimiento')
    tracking_url = fields.Char('URL de seguimiento')
    reason = fields.Char('Motivo', help='Motivo informado por Tienda Nube o el transportista (fallo, cancelación)')
    attachment_id = fields.Many2one('ir.attachment', 'PDF', ondelete='set null')

    def _tn_company(self):
        return self.sale_order_id._tn_company()

    def _update_from_tn(self, data):
        """Actualiza la etiqueta con el objeto FulfillmentOrderLabel de la API."""
        tracking = data.get('tracking_info') or {}
        history = data.get('status_history') or []
        last_reason = next((h.get('reason') for h in reversed(history) if h.get('reason')), None)
        reason = data.get('reason') or last_reason or {}
        vals = {
            'status': data.get('status') or self.status,
            'tracking_code': tracking.get('code') or self.tracking_code,
            'tracking_url': tracking.get('url') or self.tracking_url,
        }
        if reason:
            vals['reason'] = ('%s: %s' % (reason.get('type') or '', reason.get('message') or '')).strip(': ')
        self.write(vals)

    def action_download(self):
        """Descarga el PDF de la etiqueta, lo adjunta a la orden y lo abre."""
        attachments = self.env['ir.attachment']
        for label in self:
            if label.attachment_id:
                attachments |= label.attachment_id
                continue
            if label.status not in LABEL_READY:
                raise ValidationError(_(
                    'La etiqueta %s todavía no está lista para descargar (estado: %s). '
                    'Usá "Actualizar etiquetas" en unos minutos.') % (
                    label.label_id, dict(LABEL_STATUS).get(label.status, label.status)))
            company = label._tn_company()
            docs = company._tn_labels_request(
                'POST',
                '/fulfillment-orders/%s/labels/%s/download' % (label.fulfillment_order_id, label.label_id),
                params={'format': 'PDF', 'types': 'LABEL'},
            ) or []
            doc = next((d for d in docs if d.get('type') == 'LABEL'), docs[0] if docs else None)
            if not doc or not doc.get('url'):
                raise ValidationError(_('Tienda Nube no devolvió el documento de la etiqueta %s.') % label.label_id)
            pdf = requests.get(doc['url'], timeout=60)
            pdf.raise_for_status()
            order = label.sale_order_id
            attachment = self.env['ir.attachment'].create({
                'name': 'Etiqueta envío %s (%s).pdf' % (order.number_tn or order.name, label.label_id[-6:]),
                'type': 'binary',
                'datas': base64.b64encode(pdf.content),
                'res_model': 'sale.order',
                'res_id': order.id,
                'mimetype': 'application/pdf',
            })
            label.write({'attachment_id': attachment.id, 'status': 'DOWNLOADED'})
            order.message_post(
                body=_('Etiqueta de envío de Tienda Nube descargada.'),
                attachment_ids=attachment.ids,
            )
            attachments |= attachment
        if len(attachments) == 1:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%d?download=true' % attachments.id,
                'target': 'new',
            }
        return True

    @api.model
    def cron_refresh_labels(self):
        """Actualiza las etiquetas en curso y descarga las que quedaron listas."""
        since = fields.Datetime.now() - timedelta(days=3)
        labels = self.search([
            ('create_date', '>=', since),
            '|', ('status', 'in', LABEL_PENDING),
                 '&', ('status', '=', 'READY_TO_USE'), ('attachment_id', '=', False),
        ])
        for order in labels.mapped('sale_order_id'):
            try:
                with self.env.cr.savepoint():
                    order._tn_refresh_labels(download=True)
            except Exception as e:
                _logger.warning('Etiquetas TN: no se pudo actualizar %s: %s', order.name, e)
                self.env['tn.log'].create_log(
                    'Etiquetas TN: error al actualizar %s' % order.name, str(e),
                    'sale.order', order.id, 'error', traceback.format_exc())


class SaleOrderTnLabel(models.Model):
    _inherit = 'sale.order'

    tn_label_ids = fields.One2many('tn.shipping.label', 'sale_order_id', string='Etiquetas de envío TN')
    tn_label_count = fields.Integer(compute='_compute_tn_label_count')

    @api.depends('tn_label_ids')
    def _compute_tn_label_count(self):
        for order in self:
            order.tn_label_count = len(order.tn_label_ids)

    def _tn_company(self):
        self.ensure_one()
        if self.company_id.tiendanube_id:
            return self.company_id
        company = self.env['res.company'].sudo().search([('tiendanube_id', '=', self.store_id_tn)], limit=1) \
            if self.store_id_tn else False
        if not company:
            raise ValidationError(_('No se encontró la empresa de Tienda Nube de la orden %s.') % self.name)
        return company

    def _tn_fulfillment_orders(self):
        self.ensure_one()
        if not self.id_tn:
            raise ValidationError(_('La orden %s no está vinculada a Tienda Nube.') % self.name)
        return self._tn_company()._tn_labels_request(
            'GET', '/orders/%s/fulfillment-orders' % self.id_tn) or []

    def _tn_sync_labels(self, fulfillment_orders):
        """Crea/actualiza tn.shipping.label a partir de una lista de {id, labels: [...]}."""
        self.ensure_one()
        Label = self.env['tn.shipping.label']
        for fo in fulfillment_orders:
            for data in fo.get('labels') or []:
                label = Label.search([('label_id', '=', data['id'])], limit=1)
                if not label:
                    label = Label.create({
                        'sale_order_id': self.id,
                        'fulfillment_order_id': fo['id'],
                        'label_id': data['id'],
                    })
                label._update_from_tn(data)

    def _tn_refresh_labels(self, download=False):
        self.ensure_one()
        self._tn_sync_labels(self._tn_fulfillment_orders())
        if download:
            self.tn_label_ids.filtered(
                lambda l: l.status == 'READY_TO_USE' and not l.attachment_id).action_download()

    def action_tn_create_label(self):
        """Pide a Tienda Nube la etiqueta de envío de cada fulfillment order abierto."""
        self.ensure_one()
        company = self._tn_company()
        fulfillment_orders = self._tn_fulfillment_orders()
        self._tn_sync_labels(fulfillment_orders)

        with_label = self.tn_label_ids.filtered(lambda l: l.status not in LABEL_DEAD).mapped('fulfillment_order_id')
        to_request = [
            fo for fo in fulfillment_orders
            if fo.get('status') not in FO_CLOSED and fo['id'] not in with_label
        ]
        if not to_request:
            raise ValidationError(_(
                'No hay envíos para etiquetar en la orden %s: ya tienen etiqueta vigente '
                'o están entregados/cancelados.') % self.name)

        result = company._tn_labels_request(
            'POST', '/fulfillment-orders/labels', json=[{'id': fo['id']} for fo in to_request])
        self._tn_sync_labels(result or [])
        self.message_post(body=_(
            'Etiqueta de envío solicitada a Tienda Nube (%s envío/s). Se descarga sola cuando '
            'el transportista la genera, o con "Actualizar etiquetas".') % len(to_request))
        self.env['tn.log'].create_log(
            'Etiqueta solicitada %s' % self.name, 'Fulfillment orders: %s' % ', '.join(fo['id'] for fo in to_request),
            'sale.order', self.id, 'success')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Etiqueta solicitada'),
                'message': _('Tienda Nube está generando la etiqueta. Suele tardar unos segundos.'),
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def action_tn_refresh_labels(self):
        """Trae el estado de las etiquetas y descarga las listas."""
        self.ensure_one()
        self._tn_refresh_labels()
        ready = self.tn_label_ids.filtered(lambda l: l.status in LABEL_READY)
        if ready:
            return ready.action_download()
        pending = self.tn_label_ids.filtered(lambda l: l.status in LABEL_PENDING)
        failed = self.tn_label_ids.filtered(lambda l: l.status in LABEL_DEAD)
        if pending:
            message, kind = _('La etiqueta todavía se está generando. Probá de nuevo en un momento.'), 'info'
        elif failed:
            message, kind = _('La etiqueta falló: %s') % (failed[0].reason or failed[0].status), 'danger'
        else:
            message, kind = _('La orden no tiene etiquetas en Tienda Nube.'), 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _('Etiquetas Tienda Nube'), 'message': message, 'type': kind},
        }
