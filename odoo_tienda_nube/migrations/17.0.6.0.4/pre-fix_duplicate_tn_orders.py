import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Antes de agregar el constraint unico sale_order.id_tn_uniq, libera el id_tn
    de las sale.order duplicadas que pudo haber generado la condicion de carrera
    entre el webhook, el cron y los wizards de importacion de ordenes de Tienda Nube
    (ver commit que introduce id_tn_uniq / _tn_find_or_create). Por cada grupo de
    ordenes con el mismo id_tn se conserva una sola, con esta prioridad: estado
    'sale' > 'draft' > 'cancel', y entre iguales la de id mas alto (mas reciente).
    Al resto se le limpia el id_tn (no se borra el registro, solo deja de competir
    por ese id_tn) para que la migracion de esta version no falle al crear el
    constraint unico."""
    cr.execute("""
        SELECT COUNT(*) FROM (
            SELECT id_tn FROM sale_order
            WHERE id_tn IS NOT NULL
            GROUP BY id_tn HAVING COUNT(*) > 1
        ) dup
    """)
    duplicate_groups = cr.fetchone()[0]
    if not duplicate_groups:
        return

    _logger.info(
        "odoo_tienda_nube: encontrados %s id_tn duplicados en sale_order, liberando "
        "el id_tn de los perdedores antes de aplicar el constraint unico.",
        duplicate_groups,
    )
    cr.execute("""
        UPDATE sale_order SET id_tn = NULL
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY id_tn
                           ORDER BY
                               CASE state
                                   WHEN 'sale' THEN 3
                                   WHEN 'draft' THEN 2
                                   WHEN 'cancel' THEN 1
                                   ELSE 0
                               END DESC,
                               id DESC
                       ) AS rn
                FROM sale_order
                WHERE id_tn IS NOT NULL
            ) ranked
            WHERE rn > 1
        )
    """)
    _logger.info("odoo_tienda_nube: %s sale_order duplicadas resueltas.", cr.rowcount)
