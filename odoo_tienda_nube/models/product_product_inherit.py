import logging
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from .product_pricelist_inherit import TN_SKIP_PROMO_SYNC

_logger = logging.getLogger(__name__)

class TiendaNubeProductProductInherit(models.Model):
    _inherit = "product.product"

    product_id_tn = fields.Char('ID Tienda Nube', help="ID Variante Tienda Nube", copy=False)
    stock_ilimitado_tn = fields.Boolean('Stock Ilimitado en Tienda Nube', help="Stock Ilimitado en Tienda Nube")
    tn_pausar_stock_producto = fields.Boolean('Pausar sincronización de stock', help="Si esta activo este producto no sincroniza su stock con Tienda Nube (el resto de los datos del producto sigue sincronizando con normalidad)")
    precio_promocional_tn = fields.Float('Precio Promocional Tienda Nube', help="Precio promocional de Tienda Nube")
    tn_promotional_price_sent = fields.Float(
        'Precio promocional enviado a TN', copy=False, readonly=True, digits='Product Price',
        help="Ultimo precio promocional enviado a (o recibido de) Tienda Nube. La actualizacion "
             "masiva de precios solo manda las promos que cambiaron respecto de este valor.")

    #Dimensiones TN
    alto_tn = fields.Float('Alto en CM', help="Alto en Tienda Nube")
    ancho_tn = fields.Float('Ancho en CM', help="Ancho en Tienda Nube")
    profundidad_tn = fields.Float('Profundidad en CM', help="Profundidad en Tienda Nube")
    peso_tn = fields.Float('Peso en Kg', help="Peso en Tienda Nube")

    #Instagram y Google Shopping
    mpn_tn = fields.Char('MPN', help="MPN (Número de pieza del fabricante) en Tienda Nube")
    rango_edad_tn = fields.Selection([
        ('newborn', '0-3 Meses'),
        ('infant', '3-12 Meses'),
        ('toddler', '1-5 Años'),
        ('kids', '5-13 Años'),
        ('adult', 'Adulto'),
    ], string='Rango de Edad', help="Rango de Edad en Tienda Nube")
    sexo_tn = fields.Selection([
        ('unisex', 'Unisex'),
        ('male', 'Masculino'),
        ('female', 'Femenino'),
    ], string='Sexo', help="Sexo en Tienda Nube", default='unisex')

    def write(self, vals):
        res = super().write(vals)
        if 'precio_promocional_tn' in vals and not self.env.context.get(TN_SKIP_PROMO_SYNC):
            self._tn_sync_promo_to_pricelist()
        if set(vals) & set(self._tn_inventory_dimension_trigger_fields()) and self._tn_dimensions_from_inventory_enabled():
            self._tn_copy_inventory_dimensions()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        if self._tn_dimensions_from_inventory_enabled():
            products._tn_copy_inventory_dimensions()
        return products

    # ------------------------------------------------------------------
    # Medidas de Inventario -> campos Tienda Nube
    # ------------------------------------------------------------------
    @api.model
    def _tn_inventory_dimension_trigger_fields(self):
        """Campos de Inventario cuyo cambio dispara la copia a los campos TN.
        Los modulos puente (p.ej. odoo_tienda_nube_product_dimension) agregan los suyos."""
        return ['weight']

    @api.model
    def _tn_dimensions_from_inventory_enabled(self):
        return bool(self.env['res.company'].sudo().search_count([('tn_dimensions_from_inventory', '=', True)], limit=1))

    @api.model
    def _tn_convert_uom(self, value, from_uom, to_xmlid):
        to_uom = self.env.ref(to_xmlid, raise_if_not_found=False)
        if not value or not from_uom or not to_uom or from_uom == to_uom:
            return value
        return from_uom._compute_quantity(value, to_uom, round=False)

    def _tn_inventory_dimension_vals(self):
        """Valores TN (peso en kg, medidas en cm) calculados desde los campos de Inventario.
        Solo devuelve los valores mayores a 0 para no borrar lo cargado en Tienda Nube."""
        self.ensure_one()
        weight_uom = self.product_tmpl_id._get_weight_uom_id_from_ir_config_parameter()
        weight = self._tn_convert_uom(self.weight, weight_uom, 'uom.product_uom_kgm')
        return {'peso_tn': round(weight, 3)} if weight and weight > 0 else {}

    def _tn_copy_inventory_dimensions(self):
        """Copia peso/medidas de Inventario a los campos TN. Devuelve cuantas variantes cambiaron."""
        updated = 0
        for variant in self:
            vals = {
                fname: value for fname, value in variant._tn_inventory_dimension_vals().items()
                if float_compare(value, variant[fname] or 0.0, precision_digits=3) != 0
            }
            if vals:
                super(TiendaNubeProductProductInherit, variant.sudo()).write(vals)
                updated += 1
        return updated

    def action_tn_copy_inventory_dimensions(self):
        updated = self._tn_copy_inventory_dimensions()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Medidas copiadas"),
                'message': _("Se actualizaron las medidas de Tienda Nube de %s variantes.", updated),
                'type': 'success',
                'sticky': False,
            },
        }

    def _tn_promo_pending(self):
        """True si la promo actual difiere de la ultima enviada a Tienda Nube."""
        self.ensure_one()
        digits = self.env['decimal.precision'].precision_get('Product Price')
        return float_compare(self.precio_promocional_tn or 0.0, self.tn_promotional_price_sent or 0.0,
                             precision_digits=digits) != 0

    def _tn_mark_promo_sent(self):
        for variant in self:
            if variant._tn_promo_pending():
                variant.sudo().with_context(**{TN_SKIP_PROMO_SYNC: True}).write({
                    'tn_promotional_price_sent': variant.precio_promocional_tn or 0.0,
                })

    def _tn_sync_promo_to_pricelist(self):
        """Variante -> regla: si la variante tiene regla de precio fijo en la Lista de Precios Tienda Nube,
        actualiza su precio promocional. Se busca primero la regla por variante; si no hay y la plantilla
        tiene una sola variante, la regla por plantilla. Sin regla no se crea nada."""
        tn_pricelists = self.env['product.pricelist']._tn_get_tn_pricelists()
        if not tn_pricelists:
            return
        Item = self.env['product.pricelist.item'].sudo()
        base_domain = Item._tn_promo_rule_domain(tn_pricelists)
        for variant in self:
            items = Item.search(base_domain + [
                ('applied_on', '=', '0_product_variant'),
                ('product_id', '=', variant.id),
            ])
            if not items and len(variant.product_tmpl_id.with_context(active_test=False).product_variant_ids) == 1:
                items = Item.search(base_domain + [
                    ('applied_on', '=', '1_product'),
                    ('product_tmpl_id', '=', variant.product_tmpl_id.id),
                ])
            items = items.filtered(lambda i: i.tn_promotional_price != variant.precio_promocional_tn)
            if items:
                items.with_context(**{TN_SKIP_PROMO_SYNC: True}).write({
                    'tn_promotional_price': variant.precio_promocional_tn,
                })

    # Sobreescribimos unlink para que no se pueda borrar producto de descuento y envio de Tienda Nube
    def unlink(self):
        product_discount_tn = self.env.ref('odoo_tienda_nube.product_discount_tn')
        product_shipping_tn = self.env.ref('odoo_tienda_nube.product_shipping_tn')
        for product in self:
            if product.id == product_discount_tn.id:
                raise ValidationError(_("No se puede borrar el producto de descuento de Tienda Nube"))
            if product.id == product_shipping_tn.id:
                raise ValidationError(_("No se puede borrar el producto de envío de Tienda Nube"))
        return super(TiendaNubeProductProductInherit, self).unlink()
