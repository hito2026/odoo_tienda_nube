import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class stock_move_line_inherit_tn(models.Model):
    _inherit = 'stock.move.line'

    # Write
    def write(self, vals):
        res = super(stock_move_line_inherit_tn, self).write(vals)
        if self.company_id.tn_config_stock_realtime:
            self.actualizar_stock_tn()
        return res

    # Create
    @api.model
    def create(self, vals):
        res = super(stock_move_line_inherit_tn, self).create(vals)
        if res.company_id.tn_config_stock_realtime:
            res.actualizar_stock_tn()
        return res

    def actualizar_stock_tn(self):
        if self.env['res.company']._tn_sync_disabled():
            return
        for rec in self:
            if not rec.product_id.product_id_tn:
                continue

            company = rec.company_id
            if company.tn_pausar_stock_tn or rec.product_id.tn_pausar_stock_producto:
                continue
            # Si hay ubicaciones de stock TN configuradas, cualquier movimiento que toque
            # esas ubicaciones (o sus ubicaciones hijas) dispara la sincronizacion,
            # sin importar a que almacen pertenezcan.
            moves_tn_location = False
            if company.tn_stock_location_ids:
                moves_tn_location = bool(self.env['stock.location'].search_count([
                    ('id', 'in', (rec.location_id.id, rec.location_dest_id.id)),
                    ('id', 'child_of', company.tn_stock_location_ids.ids),
                ]))

            if not moves_tn_location:
                #Obtenemos location_id_tn del almacen de donde se hace el movimiento si no tiene no hacemos nada con TN
                location_id_tn = [rec.location_id.warehouse_id.location_id_tn]
                if not location_id_tn[0]:
                    continue
            else:
                warehouses = self.env['stock.warehouse'].sudo().search([('location_id_tn', '!=', False)])
                location_id_tn = warehouses.mapped('location_id_tn')
                if not location_id_tn:
                    continue

            # Actualizamos el stock en Tienda Nube
            company.update_product_stock_tn(rec.product_id, location_id_tn)
