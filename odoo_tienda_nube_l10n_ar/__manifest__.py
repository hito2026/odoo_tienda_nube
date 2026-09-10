{
    "name": "Tienda Nube - Localizacion Argentina",
    "summary": "Datos fiscales argentinos en los contactos creados desde Tienda Nube",
    "description": """
        Puente entre el conector de Tienda Nube y la localizacion argentina.

        Tienda Nube no manda la responsabilidad frente a ARCA/AFIP del comprador, asi que
        los contactos que crea el conector quedan sin ese dato y la factura no puede
        determinar bien el tipo de comprobante. Este modulo agrega:

        - Responsabilidad ARCA por defecto configurable por compania, que se aplica a los
          contactos creados desde Tienda Nube.
        - Actualizacion automatica desde el padron de ARCA cuando el contacto tiene CUIT,
          usando la conexion de la localizacion (l10n_ar_edi_ux). Si falla, no traba la
          sincronizacion: se sigue con los datos de Tienda Nube y queda una nota en la
          orden de venta para revisar los datos del contacto.
    """,
    "category": "Sale",
    "version": "19.0.1.0.0",
    "author": "Hitofusion",
    "website": "https://devoo.io",
    "license": "LGPL-3",
    "depends": [
        "odoo_tienda_nube",
        "l10n_ar",
    ],
    "data": [
        "views/res_company_inherit_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
