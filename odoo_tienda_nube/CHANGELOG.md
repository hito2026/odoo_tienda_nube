# Changelog — Tienda Nube ⇆ Odoo Connector

## [17.0.6.5.0] - 2026-11-27
### Added
- Asistente "Traer medidas desde Tienda Nube": guarda en Odoo el peso y las medidas de TN (sin enviar nada a TN), con opción de completar la pestaña Inventario vacía y de corregir la unidad a cm cuando los números coinciden con TN. Incluye simulación.

## [17.0.6.4.0] - 2026-11-26
### Added
- Umbral porcentual de stock (`tn_stock_threshold_percent`): se publica en TN el stock calculado según la configuración menos ese porcentaje, redondeado hacia abajo a entero.
- Asistente "Variantes sin match TN ↔ Odoo": lista las variantes de TN sin variante Odoo vinculada con el motivo (sin SKU, SKU inexistente o repetido, ya vinculada) y las variantes Odoo vinculadas a un ID que ya no existe en TN; permite vincular las que coinciden por SKU/código de barras.
- Opción "Tomar medidas de Inventario" (`tn_dimensions_from_inventory`): copia peso (kg) y, con el módulo `odoo_tienda_nube_product_dimension` (OCA `product_dimension`), largo/ancho/alto (cm) a los campos de TN. Botón para la carga inicial y acción en productos/variantes.

## [17.0.6.3.0] - 2026-11-26
Paridad con 19.0.
### Added
- Asistente "Importar Órdenes por Fecha" y cron cada 2 horas que trae las órdenes de ayer y hoy.
- Impuestos forzados por compañía para las líneas TN (`tn_force_tax_ids`).
- Búsqueda de contactos por documento normalizado y por email; el contacto se crea aunque la localización rechace el documento (queda un aviso en la venta). Hooks para la localización y módulo `odoo_tienda_nube_l10n_ar`.
- Grupo "Tienda Nube" para el menú y reglas multi-compañía en categorías, cupones y webhooks.
### Fixed
- Cada orden de la importación masiva va en su propia transacción; un producto que no está en Odoo se omite y queda en el log.
- El webhook hace rollback antes de liberar el lock (evita 429 en cadena).
- El batch de precios solo envía las promos que cambiaron (`tn_promotional_price_sent`): no pisa promos cargadas en el admin de TN ni hace un request por producto.
- Las líneas de descuento llevan impuestos y todos los importes TN se convierten con los impuestos efectivos de la línea (modo "Incluido" sin duplicar IVA).

## [17.0.6.2.0] - 2026-11-26
### Added
- Precio promocional TN en las reglas de la lista de precios de Tienda Nube, sincronizado con la variante.
### Fixed
- El precio enviado a TN se calcula por variante (aplican reglas por variante).
- Modo "Incluido": no se duplica el IVA en las órdenes cuando el impuesto no es "incluido en el precio".

## [17.0.6.0.0] - 2026-01-02
### Fixed
- Se modifica algorimo de actualización de precios para evitar el límite de solicitudes de Tienda Nube al realizar actualizaciones masivas.

## [17.0.5.0.0] - 2025-12-29
### Fixed
- Se completa variant_id en sincronización masiva cuando el producto no tiene variantes.

## [17.0.4.0.0] - 2025-12-16
### Added
- Se agrega una línea de venta específica para los envíos.
- Se incorpora un producto de tipo servicio, utilizado automáticamente como concepto de envío.

## [17.0.3.0.0] - 2025-11-10
### Added
- Permite contemplar **imágenes de variantes** tanto en la creación como en la actualización de imágenes en `product.template`, **a elección**.
- **CRON** para la actualización diaria de precios de productos.
- Arreglo en la publicación con más de 8 variantes.
- Asignación automática de código de barras al publicar productos en Tienda Nube.
- Limpieza de logger.
- **Galería de imágenes**: soporte para publicación y actualización de múltiples imágenes por producto.

## [17.0.2.0.0] - 2025-10-13
### Added
- Versión base para Odoo 15/16/17/18.
- Pestaña **Tienda Nube** en `res.company` con:
  - Token/Store ID, lista de precios, tipo de impuesto (incluido/no incluido).
  - Flags de sincronización de campos (nombre, categorías, publicado, envío gratis, SKU/MPN, edad, género, costo, descripción, precio promocional, dimensiones, etc.).
  - Configuración de stock (en mano/pronosticado) y **realtime** vs **CRON**.
- Campos TN en `product.template` y `product.product` (IDs, URL pública, categorías, metadatos comerciales).
- **Wizards** de importación masiva (categorías, productos, pedidos, cupones) y sincronización masiva.
- **Webhooks** con endpoint `/webhook_tn/<code_event>`, **deduplicación ~3s** y locking de ejecución.
- **CRON** “Actualizar Stock Tienda Nube” (cada 5 minutos) y actualización **en tiempo real** opcional.
- Controlador público de **imágenes** `/ati_tn_product_template_ids/<id>`.
- **Logs** (`tn.log`) con decoraciones por nivel en vistas tree/form.

### Changed
- Ajustes en vistas para exponer campos TN en productos, variantes y almacenes (`location_id_tn`).

### Fixed
- Validaciones varias ante configuraciones incompletas (sin almacenes TN, sin token, etc.).

### Security
- …
