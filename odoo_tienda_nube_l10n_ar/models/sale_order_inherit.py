import logging

from markupsafe import Markup

from odoo import _, models

_logger = logging.getLogger(__name__)

# Codigo ARCA/AFIP del tipo de documento CUIT en l10n_latam.identification.type
CUIT_AFIP_CODE = '80'


class SaleOrderTiendaNubeL10nArInherit(models.Model):
    _inherit = "sale.order"

    def _tn_prepare_partner_vals(self, order):
        """Tienda Nube no informa la responsabilidad frente a ARCA, asi que el contacto se
        crea con la que la compañia tenga configurada por defecto."""
        vals = super()._tn_prepare_partner_vals(order)
        responsibility = self.company_id.tn_default_afip_responsibility_id
        if responsibility and not vals.get('l10n_ar_afip_responsibility_type_id'):
            vals['l10n_ar_afip_responsibility_type_id'] = responsibility.id
        return vals

    def _tn_post_create_partner(self, partner, order):
        res = super()._tn_post_create_partner(partner, order)
        self._tn_update_partner_from_padron(partner)
        return res

    def _tn_partner_has_cuit(self, partner):
        identification_code = partner.l10n_latam_identification_type_id.l10n_ar_afip_code
        return bool(partner.vat) and str(identification_code or '') == CUIT_AFIP_CODE

    def _tn_update_partner_from_padron(self, partner):
        """Completa los datos fiscales del contacto recien creado desde el padron de ARCA.

        Nunca debe trabar la sincronizacion de la orden: si ARCA no responde, no encuentra
        el CUIT o falta el certificado, se sigue con los datos que mando Tienda Nube y se
        deja una nota en la venta para que revisen el contacto antes de facturar.

        La consulta va dentro de un savepoint para que un fallo a mitad de camino no deje
        la transaccion abortada y se caiga la orden entera."""
        self.ensure_one()
        if not self.company_id.tn_update_partner_from_padron:
            return False
        # get_data_from_padron_afip la aporta l10n_ar_edi_ux, que no es dependencia dura:
        # sin ese modulo el resto del puente (responsabilidad por defecto) sigue andando.
        if not hasattr(partner, 'get_data_from_padron_afip'):
            _logger.info(
                '[TN] Consulta al padron ARCA activada pero l10n_ar_edi_ux no esta instalado; '
                'se omite para el contacto %s.', partner.display_name,
            )
            return False
        if not self._tn_partner_has_cuit(partner):
            return False

        try:
            with self.env.cr.savepoint():
                padron_vals = partner.get_data_from_padron_afip()
                if padron_vals:
                    partner.write(padron_vals)
        except Exception as err:
            self._tn_notify_padron_failure(partner, err)
            return False
        return True

    def _tn_notify_padron_failure(self, partner, error):
        """Nota en la venta + log TN avisando que los datos fiscales quedaron sin verificar."""
        self.ensure_one()
        message = _(
            "No se pudieron traer los datos del padrón de ARCA para el contacto %(partner)s "
            "(CUIT %(vat)s). La orden se sincronizó igual con los datos que envió Tienda Nube: "
            "verificá la responsabilidad ARCA y la razón social del contacto antes de facturar.",
            partner=partner.display_name,
            vat=partner.vat or '',
        )
        _logger.warning('[TN] Orden %s: %s (%s)', self.id_tn, message, error)
        self.message_post(body=Markup('%s<br/><br/>%s') % (message, str(error)))
        self.env['tn.log'].create_log(
            _('Padrón ARCA sin consultar — %s') % (self.name or ''),
            message,
            'sale.order',
            self.id,
            'warning',
            str(error),
        )
