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
        return res

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
