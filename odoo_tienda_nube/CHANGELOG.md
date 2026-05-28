# Changelog — Tienda Nube ⇆ Odoo Connector

## [18.0.7.0.6] - 2026-05-28

### Fixed

- En el wizard de sincronización masiva por código de barras/SKU, `variant_tn_id` ahora se completa siempre con el ID de variante de Tienda Nube (`variant.id`), evitando guardar el ID de producto/template en publicaciones de una sola variante.
- En la importación de órdenes desde Tienda Nube, se agrega un fallback de resolución de producto: si no existe coincidencia por `product.product.product_id_tn` y el `product.template.id_tn` está mapeado con una sola variante en Odoo, se usa esa variante automáticamente y se completa `product_id_tn` con el `variant_id` recibido.

## [18.0.7.0.5] - 2026-04-22

### Added

- Al crear un nuevo contacto desde la sincronización de órdenes de Tienda Nube, se asigna automáticamente el tipo de responsabilidad AFIP (`l10n_ar_afip_responsibility_type_id`) en base al campo `billing_customer_type` recibido en la orden. Solo aplica cuando la compañía es argentina y el módulo de localización argentina (`l10n_ar`) está instalado. Si el campo no viene informado, se asigna **Consumidor Final** por defecto. Los contactos ya existentes en Odoo no son modificados.

## [18.0.7.0.2] - 2026-02-12
### Fixed

- Se modifica para que tome los descuento de medio de pago que viene de TN

## [18.0.7.0.1] - 2026-02-01

### Fixed

- Se modifica el wizard de Creación masiva de productos para evitar que si una categoria no esta en odoo, no envia a la
  lista de productos, una categoria en false, y control de error para que no falle el proceso.


## [18.0.7.0.0] - 2026-01-22

### Added

- Asociación de compañía en categorías y cupones.Reglas específicas para el manejo multicompañía en ambos casos.

## [18.0.6.0.0] - 2025-12-31

### Fixed

- Se modifica algorimo de actualización de precios para evitar el límite de solicitudes de Tienda Nube al realizar
  actualizaciones masivas.

## [18.0.5.0.0] - 2025-12-29

### Fixed

- Se completa variant_id en sincronización masiva cuando el producto no tiene variantes.

## [18.0.4.0.0] - 2025-12-16

### Added

- Se agrega una línea de venta específica para los envíos.
- Se incorpora un producto de tipo servicio, utilizado automáticamente como concepto de envío.

## [18.0.3.0.0] - 2025-11-10

### Added

- Permite contemplar **imágenes de variantes** tanto en la creación como en la actualización de imágenes en
  `product.template`, **a elección**.
- **CRON** para la actualización diaria de precios de productos.
- Arreglo en la publicación con más de 8 variantes.
- Asignación automática de código de barras al publicar productos en Tienda Nube.
- Limpieza de logger.
- **Galería de imágenes**: soporte para publicación y actualización de múltiples imágenes por producto.

## [18.0.2.0.0] - 2025-10-13

### Added

- Versión base para Odoo 15/16/17/18.
- Pestaña **Tienda Nube** en `res.company` con:
    - Token/Store ID, lista de precios, tipo de impuesto (incluido/no incluido).
    - Flags de sincronización de campos (nombre, categorías, publicado, envío gratis, SKU/MPN, edad, género, costo,
      descripción, precio promocional, dimensiones, etc.).
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
