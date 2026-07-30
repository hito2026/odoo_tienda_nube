{
    "name": "Tienda Nube - Auto Facturacion y Pagos",
    "summary": "Automatiza confirmacion, facturacion, pago y conciliacion para ordenes TN",
    "description": """
        Automatizacion contable para ordenes de Tienda Nube en Odoo.

        Funcionalidades:
        - Confirma automaticamente la orden cuando el pago en TN esta confirmado.
        - Crea la factura al validar el picking de salida.
        - Genera el pago automatico segun el mapeo metodo TN -> diario Odoo.
        - Concilia el pago con la factura y marca la orden como completa.
        - Registra warnings cuando falta el mapeo o cuando la conciliacion requiere intervencion manual.

        Uso:
        1. Configurar el mapeo de metodos de pago en Tienda Nube > Configuracion.
        2. Asegurar que la orden llegue con payment_status TN en paid o authorized.
        3. Validar el picking de salida para disparar la facturacion y el cobro.
    """,
    "category": "Sale",
    "version": "19.0.1.1.0",
    "author": "Hitofusion",
    "website": "https://devoo.io",
    "license": "LGPL-3",
    "depends": [
        "odoo_tienda_nube",
        "sale_management",
        "stock",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_inherit_view.xml",
        "views/tn_payment_method_mapping_views.xml",
        "views/sale_order_inherit_view.xml",
    ],
    "images": [
        "static/description/icon.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
