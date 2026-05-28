{
    "name": "Tienda Nube - Auto Facturacion y Pagos",
    "summary": "Automatiza confirmacion, facturacion, pago y conciliacion para ordenes TN",
    "category": "Sale",
    "version": "18.0.1.0.0",
    "author": "Hitofusion",
    "license": "LGPL-3",
    "depends": [
        "odoo_tienda_nube",
        "sale_management",
        "stock",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/tn_payment_method_mapping_views.xml",
        "views/sale_order_inherit_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
