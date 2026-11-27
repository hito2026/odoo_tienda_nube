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

    def _tn_inventory_vals_from_tn(self, dims, fill_inventory=False, fix_uom=False):
        vals, actions = super()._tn_inventory_vals_from_tn(dims, fill_inventory=fill_inventory, fix_uom=fix_uom)
        tn_values = [dims.get(TN_DIMENSION_MAP[src], 0) for src in TN_DIMENSION_MAP]
        odoo_values = [self[src] for src in TN_DIMENSION_MAP]
        if not any(v > 0 for v in tn_values):
            return vals, actions
        cm = self.env.ref('uom.product_uom_cm')
        if fill_inventory and not any(odoo_values):
            vals.update({src: value for src, value in zip(TN_DIMENSION_MAP, tn_values) if value > 0})
            vals['dimensional_uom_id'] = cm.id
            actions.add('inventory_filled')
        elif (fix_uom and any(odoo_values) and self.dimensional_uom_id != cm
              and self._tn_same_measures(odoo_values, tn_values)):
            # Los numeros cargados coinciden con TN (en cm): la unidad estaba mal elegida
            vals['dimensional_uom_id'] = cm.id
            actions.add('uom_fixed')
        return vals, actions

    @api.model
    def _tn_same_measures(self, values, other, tolerance=0.5):
        """Mismas medidas aunque esten cargadas en otro orden (largo/ancho/alto cruzados)."""
        return all(abs(a - b) <= tolerance for a, b in zip(sorted(values), sorted(other)))
