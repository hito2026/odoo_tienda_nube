# Changelog

## 19.0.1.1.1 - 2026-09-10

### Fixed
- Error `Invalid field account.payment.ref` al validar el picking: desde Odoo 18 `account.payment` ya no toma `ref` por delegacion de `account.move` y el campo se llama `memo`. Se resuelve el nombre en runtime (`_tn_payment_memo_field`) para mantener compatibilidad con 17.0.

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
