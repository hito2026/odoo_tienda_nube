from odoo import fields, models


class TestConnectionTnWizard(models.TransientModel):
    _name = 'test.connection.tn.wizard'
    _description = 'Wizard para probar conexión con Tienda Nube'

    success = fields.Boolean('Conexión exitosa', readonly=True)
    message = fields.Text('Mensaje', readonly=True)
