import logging

from odoo import _, models

_logger = logging.getLogger(__name__)

# Codigo ARCA/AFIP del tipo de documento CUIT en l10n_latam.identification.type
CUIT_AFIP_CODE = '80'


class SaleOrderTiendaNubeL10nArInherit(models.Model):
    _inherit = "sale.order"

    def _tn_identification_variants(self, identification):
        """Ademas del numero pelado, los formatos con que se suelen cargar a mano en Odoo:
        DNI con puntos (30.123.456) y CUIT/CUIL con guiones (20-30123456-7)."""
        variants = super()._tn_identification_variants(identification)
        if identification.isdigit():
            if len(identification) == 8:
                variants.add('%s.%s.%s' % (identification[:2], identification[2:5], identification[5:]))
            elif len(identification) == 7:
                variants.add('%s.%s.%s' % (identification[:1], identification[1:4], identification[4:]))
            elif len(identification) == 11:
                variants.add('%s-%s-%s' % (identification[:2], identification[2:10], identification[10:]))
        return variants

    def _tn_get_identification_type(self, order, identification):
        """Tipo de documento argentino por la cantidad de digitos, que manda sobre lo que
        declare Tienda Nube: si el comprador eligio "DNI" pero cargo su CUIT, marcarlo como
        DNI hace fallar la validacion de ARCA. 7-8 digitos es DNI; 11 es CUIT, o CUIL si
        TN lo declaro asi. Se usan los xmlid de l10n_ar en vez de buscar por nombre."""
        if identification.isdigit():
            declared = str(order.get('billing_document_type') or '').strip().upper()
            xmlid = False
            if len(identification) in (7, 8):
                xmlid = 'l10n_ar.it_dni'
            elif len(identification) == 11:
                xmlid = 'l10n_ar.it_CUIL' if declared == 'CUIL' else 'l10n_ar.it_cuit'
            id_type = self.env.ref(xmlid, raise_if_not_found=False) if xmlid else False
            if id_type:
                return id_type
        return super()._tn_get_identification_type(order, identification)

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

    def _tn_post_find_partner(self, partner, order):
        res = super()._tn_post_find_partner(partner, order)
        self._tn_complete_partner_fiscal_data(partner)
        return res

    def _tn_complete_partner_fiscal_data(self, partner):
        """Completa la responsabilidad ARCA de un contacto que ya existia y se reusa para
        una orden de Tienda Nube.

        La responsabilidad se cargaba solo al crear el contacto, asi que los que ya estaban
        en la base (compras anteriores, otros canales, altas manuales) se quedaban sin ella
        y la factura no podia determinar el tipo de comprobante.

        Solo se completa si esta vacia: nunca se pisa lo que alguien cargo a mano. Al padron
        se le pega unicamente si el contacto tiene CUIT, que es el unico caso en el que ARCA
        puede decir algo; un consumidor final con DNI no se consulta."""
        self.ensure_one()
        if partner.l10n_ar_afip_responsibility_type_id:
            return False

        if self._tn_partner_has_cuit(partner):
            self._tn_update_partner_from_padron(partner)
            if partner.l10n_ar_afip_responsibility_type_id:
                return True

        responsibility = self.company_id.tn_default_afip_responsibility_id
        if not responsibility:
            return False
        partner.l10n_ar_afip_responsibility_type_id = responsibility
        return True

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
        self._tn_notify_partner_issue(partner, _(
            "No se pudieron traer los datos del padrón de ARCA para el contacto %(partner)s "
            "(CUIT %(vat)s). La orden se sincronizó igual con los datos que envió Tienda Nube: "
            "verificá la responsabilidad ARCA y la razón social del contacto antes de facturar.",
            partner=partner.display_name,
            vat=partner.vat or '',
        ), error)
