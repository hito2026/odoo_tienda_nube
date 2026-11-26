import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _init_promo_sent(cr):
    """tn_promotional_price_sent es nuevo: se asume que la promo que hoy tiene cada variante
    sincronizada ya esta en Tienda Nube, para que la primera actualizacion masiva no mande
    la promo de todo el catalogo."""
    cr.execute("""
        UPDATE product_product
           SET tn_promotional_price_sent = COALESCE(precio_promocional_tn, 0)
         WHERE product_id_tn IS NOT NULL
    """)
    _logger.info("[TN] tn_promotional_price_sent inicializado en %s variantes", cr.rowcount)


def migrate(cr, version):
    _init_promo_sent(cr)
    _tn_assign_group(cr)


def _tn_assign_group(cr):
    """El menu de Tienda Nube pasa a requerir el grupo 'Tienda Nube'. Para que nadie que lo
    usaba lo pierda al actualizar, se asigna a los usuarios internos que ya tenian acceso
    de gerente de ventas (los administradores lo reciben por implied_ids)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    group = env.ref('odoo_tienda_nube.group_tienda_nube_user', raise_if_not_found=False)
    sale_manager = env.ref('sales_team.group_sale_manager', raise_if_not_found=False)
    if not group or not sale_manager:
        return
    users = sale_manager.all_user_ids.filtered(lambda u: u.active and not u.share) - group.user_ids
    if users:
        group.user_ids = [(4, user.id) for user in users]
    _logger.info("[TN] Grupo Tienda Nube asignado a %s usuarios gerentes de ventas", len(users))
