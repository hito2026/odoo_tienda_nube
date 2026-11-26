# Changelog

## 17.0.1.2.1 - 2026-11-26

Backport de 19.0.1.2.0 / 19.0.1.2.1.

### Added
- Validacion automatica del remito al confirmarse la orden TN (`tn_auto_validate_picking`), que encadena factura, pago y conciliacion. Valida la cadena completa en rutas de varios pasos y solo si Tienda Nube informa el pago como paid o authorized.
- Opcion `tn_auto_validate_without_stock`: por defecto no se valida si los movimientos no estan completamente reservados y queda el aviso en la venta.

### Fixed
- La factura se publica con `l10n_ar_invoice_skip_commit` dentro de su propio savepoint: si ARCA la rechaza queda en borrador con el error en el log y el chatter, sin deshacer la orden importada.
- Una factura TN que habia quedado en borrador no se volvia a intentar publicar.
- Creacion de factura, pago, conciliacion y confirmacion automatica van en savepoints.

## 18.0.1.1.0 - 2026-05-29

### Added
- Configuracion de disparador de facturacion automatica TN por compania (PICK/OUT).
- Fallback automatico a OUT cuando la ruta no tiene pickings internos (one-step delivery).
- Campo de diario de facturacion TN predeterminado en compania.
- Uso del diario de facturacion TN al crear factura automatica.
- Creacion automatica de mapeos de metodo de pago TN cuando no existen.
- Vista y metadatos de Apps mejorados (icono y descripcion de modulo).

### Changed
- La configuracion de disparador TN se persiste por compania en `ir.config_parameter` para evitar dependencia de columna SQL.
- El mapeo de metodo de pago TN permite guardar sin diario para completar luego.

### Fixed
- Decorador invalido de compute (`fields.depends`) reemplazado por `api.depends`.
- Error de transaccion abortada al intentar crear mapeo TN sin diario en bases con `NOT NULL` heredado.
- Error de parseo de vista por campo faltante `tn_invoice_journal_id`.
- Error de carga por `depends('id')` no permitido en Odoo.
