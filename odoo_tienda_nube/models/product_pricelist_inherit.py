from odoo import api, fields, models

# Contexto para cortar la sincronizacion bidireccional del precio promocional
# (regla de lista <-> variante) y evitar escrituras en loop.
TN_SKIP_PROMO_SYNC = 'tn_skip_promo_sync'


class TiendaNubeProductPricelistInherit(models.Model):
    _inherit = 'product.pricelist'

    tn_is_tn_pricelist = fields.Boolean(
        'Es lista de Tienda Nube',
        compute='_compute_tn_is_tn_pricelist',
        help="Indica si la lista esta configurada como Lista de Precios Tienda Nube en alguna compañia",
    )

    def _tn_get_tn_pricelists(self):
        return self.env['res.company'].sudo().search([('tn_pricelist_id', '!=', False)]).tn_pricelist_id

    def _compute_tn_is_tn_pricelist(self):
        tn_pricelists = self._tn_get_tn_pricelists()
        for pricelist in self:
            pricelist.tn_is_tn_pricelist = pricelist._origin in tn_pricelists


class TiendaNubeProductPricelistItemInherit(models.Model):
    _inherit = 'product.pricelist.item'

    tn_promotional_price = fields.Float(
        'Precio promocional TN',
        digits='Product Price',
        help="Precio promocional que se publica en Tienda Nube (el precio de la regla se muestra tachado). "
             "Solo aplica a reglas de precio fijo de la Lista de Precios Tienda Nube. "
             "Se sincroniza con el campo 'Precio Promocional Tienda Nube' de la variante. "
             "Dejar en 0 para no publicar promoción.",
    )
    tn_is_tn_pricelist = fields.Boolean(related='pricelist_id.tn_is_tn_pricelist')

    @api.model
    def _tn_promo_rule_domain(self, pricelists):
        return [
            ('pricelist_id', 'in', pricelists.ids),
            ('compute_price', '=', 'fixed'),
            ('min_quantity', '<=', 1),
        ]

    def _tn_is_promo_rule(self, tn_pricelists):
        self.ensure_one()
        return (
            self.pricelist_id in tn_pricelists
            and self.compute_price == 'fixed'
            and self.min_quantity <= 1
            and self.applied_on in ('0_product_variant', '1_product')
        )

    def _tn_sync_promo_to_variants(self):
        """Regla -> variante: copia tn_promotional_price al precio promocional de las variantes alcanzadas.
        Una regla por plantilla no pisa variantes que tengan su propia regla por variante en la misma lista."""
        if self.env.context.get(TN_SKIP_PROMO_SYNC):
            return
        tn_pricelists = self.env['product.pricelist']._tn_get_tn_pricelists()
        if not tn_pricelists:
            return
        Item = self.env['product.pricelist.item'].sudo()
        for item in self:
            if not item._tn_is_promo_rule(tn_pricelists):
                continue
            if item.applied_on == '0_product_variant':
                variants = item.product_id
            else:
                variants = item.product_tmpl_id.with_context(active_test=False).product_variant_ids
                with_own_rule = Item.search(item._tn_promo_rule_domain(item.pricelist_id) + [
                    ('applied_on', '=', '0_product_variant'),
                    ('product_id', 'in', variants.ids),
                ]).product_id
                variants -= with_own_rule
            variants = variants.filtered(lambda v: v.precio_promocional_tn != item.tn_promotional_price)
            if variants:
                variants.sudo().with_context(**{TN_SKIP_PROMO_SYNC: True}).write({
                    'precio_promocional_tn': item.tn_promotional_price,
                })

    @api.model_create_multi
    def create(self, vals_list):
        items = super().create(vals_list)
        to_sync = items.browse([item.id for item, vals in zip(items, vals_list) if 'tn_promotional_price' in vals])
        to_sync._tn_sync_promo_to_variants()
        return items

    def write(self, vals):
        res = super().write(vals)
        if 'tn_promotional_price' in vals:
            self._tn_sync_promo_to_variants()
        elif {'product_id', 'product_tmpl_id', 'applied_on', 'compute_price', 'pricelist_id', 'min_quantity'} & set(vals):
            # Cambio el alcance de la regla: solo se propaga si la regla tiene promo cargada,
            # para no borrar la promo de la variante nueva con un 0.
            self.filtered('tn_promotional_price')._tn_sync_promo_to_variants()
        return res
