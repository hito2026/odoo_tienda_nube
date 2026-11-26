import logging

_logger = logging.getLogger(__name__)


def _tn_default_company(cr):
    """Compañia a asignar a categorias y cupones existentes: la unica conectada a Tienda
    Nube si hay una sola; si no, la primera compañia."""
    cr.execute("""
        SELECT id FROM res_company
        WHERE tiendanube_id IS NOT NULL AND tiendanube_id != ''
          AND tiendanube_access_token IS NOT NULL AND tiendanube_access_token != ''
        ORDER BY id
    """)
    rows = cr.fetchall()
    if len(rows) == 1:
        return rows[0][0]
    if len(rows) > 1:
        _logger.warning(
            "[TN] Hay %s compañias conectadas a Tienda Nube: categorias y cupones existentes "
            "se asignan a la compañia %s. Revisar y reasignar si corresponde.", len(rows), rows[0][0])
        return rows[0][0]
    cr.execute("SELECT id FROM res_company ORDER BY id LIMIT 1")
    return cr.fetchone()[0]


def migrate(cr, version):
    """category.tn y coupon.tn pasan a tener company_id obligatorio (reglas multi-compañia).
    Se crea la columna y se completa antes de que el ORM agregue el NOT NULL, para no
    depender de env.company al actualizar (con varias compañias las categorias podrian
    quedar en una compañia que no usa Tienda Nube y desaparecer por la regla)."""
    company_id = _tn_default_company(cr)
    for table in ('category_tn', 'coupon_tn'):
        cr.execute("ALTER TABLE %s ADD COLUMN IF NOT EXISTS company_id integer" % table)
        cr.execute("UPDATE %s SET company_id = %%s WHERE company_id IS NULL" % table, (company_id,))
        _logger.info("[TN] %s: %s registros asignados a la compañia %s", table, cr.rowcount, company_id)
