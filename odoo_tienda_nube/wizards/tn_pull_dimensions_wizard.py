import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class _DryRun(Exception):
    pass


class TnPullDimensionsWizard(models.TransientModel):
    _name = 'tn.pull.dimensions.wizard'
    _description = 'Traer medidas y peso desde Tienda Nube'

    company_id = fields.Many2one('res.company', 'Compañía', required=True, default=lambda self: self.env.company)
    fill_inventory = fields.Boolean(
        'Completar Inventario vacío', default=True,
        help="Si la variante no tiene peso o medidas en la pestaña Inventario, se cargan los de Tienda Nube "
             "(peso en kg, medidas en cm). Nunca se pisa un valor de Inventario ya cargado.")
    fix_uom = fields.Boolean(
        'Corregir unidad cuando coincide con TN', default=True,
        help="Si las medidas de Inventario estan en otra unidad (p.ej. metros) pero los numeros coinciden con "
             "los de Tienda Nube en cm, se cambia la unidad a cm sin tocar los numeros.")
    state = fields.Selection([('draft', 'Borrador'), ('simulated', 'Simulado'), ('done', 'Aplicado')], default='draft')
    tn_variant_count = fields.Integer('Variantes vinculadas con datos en TN', readonly=True)
    tn_updated_count = fields.Integer('Campos TN actualizados', readonly=True)
    inventory_filled_count = fields.Integer('Inventario completado', readonly=True)
    uom_fixed_count = fields.Integer('Unidad corregida a cm', readonly=True)
    without_tn_data_count = fields.Integer('Vinculadas sin variante en TN', readonly=True)

    @api.model
    def _tn_dims_from_variant(self, variant):
        to_float = lambda value: float(value or 0)
        return {
            'peso_tn': to_float(variant.get('weight')),
            'profundidad_tn': to_float(variant.get('depth')),
            'ancho_tn': to_float(variant.get('width')),
            'alto_tn': to_float(variant.get('height')),
        }

    def _tn_fetch_dimensions(self):
        """{id TN: medidas} por ID de variante y, para productos de una sola variante, tambien por ID de producto."""
        company = self.company_id
        if not company.tiendanube_id or not company.tiendanube_access_token:
            raise UserError(_("La compañía %s no tiene Tienda Nube configurada.", company.name))
        result = {}
        for product in company.get_all_products_tn() or []:
            variants = product.get('variants') or []
            for variant in variants:
                result[str(variant['id'])] = self._tn_dims_from_variant(variant)
            if len(variants) == 1:
                result.setdefault(str(product['id']), result[str(variants[0]['id'])])
        return result

    def _run(self, dry_run):
        self.ensure_one()
        tn_dims = self._tn_fetch_dimensions()
        variants = self.env['product.product'].with_context(active_test=False).search([
            ('product_id_tn', '!=', False),
            '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id),
        ])
        counts = dict.fromkeys(('tn_updated', 'inventory_filled', 'uom_fixed'), 0)
        found = missing = 0
        try:
            with self.env.cr.savepoint():
                for variant in variants:
                    dims = tn_dims.get(variant.product_id_tn)
                    if not dims:
                        missing += 1
                        continue
                    found += 1
                    for action in variant._tn_apply_tn_dimensions(
                            dims, fill_inventory=self.fill_inventory, fix_uom=self.fix_uom):
                        counts[action] += 1
                if dry_run:
                    raise _DryRun()
        except _DryRun:
            self.env.invalidate_all()
        self.write({
            'state': 'simulated' if dry_run else 'done',
            'tn_variant_count': found,
            'without_tn_data_count': missing,
            'tn_updated_count': counts['tn_updated'],
            'inventory_filled_count': counts['inventory_filled'],
            'uom_fixed_count': counts['uom_fixed'],
        })
        if not dry_run:
            _logger.info("Medidas traidas de Tienda Nube (compañia %s): %s", self.company_id.name, counts)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_simulate(self):
        return self._run(dry_run=True)

    def action_apply(self):
        return self._run(dry_run=False)
