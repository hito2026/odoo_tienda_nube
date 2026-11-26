from odoo import fields, models


class TiendaNubeResCompanyL10nArInherit(models.Model):
    _inherit = "res.company"

    tn_default_afip_responsibility_id = fields.Many2one(
        'l10n_ar.afip.responsibility.type',
        string='Responsabilidad ARCA por defecto (TN)',
        help="Responsabilidad frente a ARCA/AFIP que se asigna a los contactos creados a "
             "partir de una orden de Tienda Nube. Tienda Nube no informa este dato, y sin el "
             "la factura no puede determinar el tipo de comprobante. Lo habitual es "
             "'Consumidor Final'. Si se activa la consulta al padron y el contacto tiene "
             "CUIT, la responsabilidad que devuelve ARCA pisa a esta.",
    )
    tn_update_partner_from_padron = fields.Boolean(
        string='Consultar padron ARCA al crear el contacto (TN)',
        help="Si esta activo, cuando el conector crea un contacto con CUIT se consultan sus "
             "datos en el padron de ARCA y se completan razon social, domicilio y "
             "responsabilidad. Requiere la localizacion con certificado ARCA configurado. "
             "Si la consulta falla la orden se sincroniza igual y queda una nota en la venta.",
    )
