from odoo import api, models

# Campo Inventario (product_dimension) -> campo Tienda Nube (en cm)
TN_DIMENSION_MAP = {
    'product_length': 'profundidad_tn',
    'product_width': 'ancho_tn',
    'product_height': 'alto_tn',
}


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _tn_inventory_dimension_trigger_fields(self):
        return super()._tn_inventory_dimension_trigger_fields() + list(TN_DIMENSION_MAP) + ['dimensional_uom_id']

    def _tn_inventory_dimension_vals(self):
        vals = super()._tn_inventory_dimension_vals()
        for src, dst in TN_DIMENSION_MAP.items():
            value = self._tn_convert_uom(self[src], self.dimensional_uom_id, 'uom.product_uom_cm')
            if value and value > 0:
                vals[dst] = round(value, 2)
        return vals
