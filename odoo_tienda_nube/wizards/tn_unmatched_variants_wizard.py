from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

UNMATCHED_REASONS = [
    ('matchable', 'Se puede vincular (SKU/código libre en Odoo)'),
    ('no_code', 'Sin SKU ni código de barras en TN'),
    ('not_found', 'SKU/código no existe en Odoo'),
    ('duplicated', 'SKU/código repetido en Odoo'),
    ('linked_other', 'La variante Odoo ya está vinculada a otra variante TN'),
    ('odoo_orphan', 'Vinculada en Odoo a una variante que ya no existe en TN'),
]


class TnUnmatchedVariantsWizard(models.TransientModel):
    _name = 'tn.unmatched.variants.wizard'
    _description = 'Variantes sin match entre Tienda Nube y Odoo'

    company_id = fields.Many2one('res.company', 'Compañía', required=True, default=lambda self: self.env.company)
    line_ids = fields.One2many('tn.unmatched.variants.line', 'wizard_id', 'Variantes')
    tn_variant_count = fields.Integer('Variantes en TN', readonly=True)
    matched_count = fields.Integer('Vinculadas', readonly=True)
    tn_unmatched_count = fields.Integer('De TN sin match', readonly=True)
    odoo_orphan_count = fields.Integer('De Odoo sin variante en TN', readonly=True)

    # ------------------------------------------------------------------
    @api.model
    def _tn_variant_label(self, product, variant):
        values = [v.get('es') or next(iter(v.values()), '') for v in variant.get('values') or []]
        name = (product.get('name') or {}).get('es') or ''
        return "%s (%s)" % (name, ", ".join(values)) if values else name

    def _tn_odoo_code_index(self, field_name, codes):
        """{codigo: variantes Odoo} para los SKU/códigos de barras de TN, en una sola búsqueda."""
        index = defaultdict(lambda: self.env['product.product'])
        codes = [c for c in codes if c]
        if not codes:
            return index
        Product = self.env['product.product'].with_context(active_test=False)
        for product in Product.search([(field_name, 'in', codes)]):
            index[product[field_name]] |= product
        return index

    def action_analyze(self):
        self.ensure_one()
        company = self.company_id
        if not company.tiendanube_id or not company.tiendanube_access_token:
            raise UserError(_("La compañía %s no tiene Tienda Nube configurada.", company.name))
        tn_products = company.get_all_products_tn() or []

        Product = self.env['product.product'].with_context(active_test=False)
        linked = Product.search([('product_id_tn', '!=', False)])
        linked_by_tn_id = {p.product_id_tn: p for p in linked}
        tn_tmpl_ids = set(self.env['product.template'].with_context(active_test=False).search(
            [('id_tn', '!=', False)]).mapped('id_tn'))

        variants = [(p, v) for p in tn_products for v in (p.get('variants') or [])]
        sku_index = self._tn_odoo_code_index('default_code', [v.get('sku') for _p, v in variants])
        barcode_index = self._tn_odoo_code_index('barcode', [v.get('barcode') for _p, v in variants])

        seen_tn_ids = set()
        lines = []
        matched = 0
        for product, variant in variants:
            product_tn_id = str(product['id'])
            variant_tn_id = str(variant['id'])
            single = len(product.get('variants') or []) == 1
            seen_tn_ids.add(variant_tn_id)
            if single:
                # Para productos de una sola variante el asistente por código de barras guarda el ID del producto
                seen_tn_ids.add(product_tn_id)
            if variant_tn_id in linked_by_tn_id or (single and (
                    product_tn_id in linked_by_tn_id or product_tn_id in tn_tmpl_ids)):
                matched += 1
                continue

            sku, barcode = variant.get('sku') or '', variant.get('barcode') or ''
            candidates = (sku and sku_index.get(sku)) or (barcode and barcode_index.get(barcode)) or Product
            if not sku and not barcode:
                reason = 'no_code'
            elif not candidates:
                reason = 'not_found'
            elif len(candidates) > 1:
                reason = 'duplicated'
            elif candidates.product_id_tn:
                reason = 'linked_other'
            else:
                reason = 'matchable'
            lines.append((0, 0, {
                'origin': 'tn',
                'reason': reason,
                'tn_product_id': product_tn_id,
                'tn_variant_id': variant_tn_id,
                'tn_single_variant': single,
                'tn_name': self._tn_variant_label(product, variant),
                'tn_sku': sku,
                'tn_barcode': barcode,
                'tn_published': bool(product.get('published')),
                'odoo_product_id': candidates[:1].id,
                'odoo_candidate_count': len(candidates),
            }))

        orphans = [p for tn_id, p in linked_by_tn_id.items() if tn_id not in seen_tn_ids]
        for product in orphans:
            lines.append((0, 0, {
                'origin': 'odoo',
                'reason': 'odoo_orphan',
                'tn_variant_id': product.product_id_tn,
                'tn_product_id': product.product_tmpl_id.id_tn,
                'odoo_product_id': product.id,
                'odoo_candidate_count': 1,
            }))

        self.line_ids = [(5, 0, 0)] + lines
        self.write({
            'tn_variant_count': len(variants),
            'matched_count': matched,
            'tn_unmatched_count': len(lines) - len(orphans),
            'odoo_orphan_count': len(orphans),
        })
        return self._action_reopen()

    def _action_reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_open_lines(self):
        """Abre las variantes en una lista completa (filtrable, agrupable y exportable)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Variantes sin match TN ↔ Odoo"),
            'res_model': 'tn.unmatched.variants.line',
            'view_mode': 'tree',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'search_default_group_reason': 1},
            'target': 'current',
        }

    def action_link_matchable(self):
        self.ensure_one()
        to_link = self.line_ids.filtered(lambda l: l.reason == 'matchable')
        if not to_link:
            raise UserError(_("No hay variantes para vincular."))
        to_link.action_link()
        return self._action_reopen()


class TnUnmatchedVariantsLine(models.TransientModel):
    _name = 'tn.unmatched.variants.line'
    _description = 'Variante sin match entre Tienda Nube y Odoo'
    _order = 'origin desc, reason, tn_name'

    wizard_id = fields.Many2one('tn.unmatched.variants.wizard', required=True, ondelete='cascade')
    origin = fields.Selection([('tn', 'Tienda Nube'), ('odoo', 'Odoo')], 'Falta en', readonly=True,
                              help="Tienda Nube: la variante existe en TN y no tiene variante Odoo vinculada. "
                                   "Odoo: la variante Odoo apunta a un ID de TN que ya no existe.")
    reason = fields.Selection(UNMATCHED_REASONS, 'Motivo', readonly=True)
    tn_product_id = fields.Char('ID producto TN', readonly=True)
    tn_variant_id = fields.Char('ID variante TN', readonly=True)
    tn_single_variant = fields.Boolean('Producto TN de una variante', readonly=True)
    tn_name = fields.Char('Producto en TN', readonly=True)
    tn_sku = fields.Char('SKU en TN', readonly=True)
    tn_barcode = fields.Char('Código de barras en TN', readonly=True)
    tn_published = fields.Boolean('Publicado en TN', readonly=True)
    odoo_product_id = fields.Many2one('product.product', 'Variante Odoo', readonly=True)
    odoo_default_code = fields.Char(related='odoo_product_id.default_code', string='Referencia Odoo')
    odoo_product_id_tn = fields.Char(related='odoo_product_id.product_id_tn', string='ID TN en Odoo')
    odoo_candidate_count = fields.Integer('Coincidencias en Odoo', readonly=True)

    def action_link(self):
        """Vincula la variante Odoo encontrada por SKU/código con la variante de TN
        (mismo criterio que 'Sincronizar Masivamente Productos TN-Odoo')."""
        for line in self:
            if line.reason != 'matchable' or not line.odoo_product_id:
                raise ValidationError(_("Solo se pueden vincular las variantes con motivo '%s'.",
                                        dict(UNMATCHED_REASONS)['matchable']))
            product = line.odoo_product_id
            template = product.product_tmpl_id
            if template.id_tn and template.id_tn != line.tn_product_id:
                raise ValidationError(_(
                    "La variante %(variant)s pertenece a un producto Odoo vinculado a otro producto de TN "
                    "(%(odoo_tn)s, en TN es %(tn)s). Revisalo a mano.",
                    variant=product.display_name, odoo_tn=template.id_tn, tn=line.tn_product_id))
            product.product_id_tn = line.tn_variant_id
            if not template.id_tn:
                template.id_tn = line.tn_product_id
        for wizard in self.wizard_id:
            count = len(self.filtered(lambda l: l.wizard_id == wizard))
            wizard.write({
                'matched_count': wizard.matched_count + count,
                'tn_unmatched_count': wizard.tn_unmatched_count - count,
            })
        self.unlink()
        return True
