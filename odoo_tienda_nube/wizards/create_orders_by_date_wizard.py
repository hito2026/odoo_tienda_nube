from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CreateOrdersByDateWizard(models.TransientModel):
    _name = 'create.orders.by.date.wizard'
    _description = 'Wizard para crear órdenes por rango de fechas'

    date_from = fields.Date(
        string='Fecha desde',
        required=True,
        default=fields.Date.today,
    )
    date_to = fields.Date(
        string='Fecha hasta',
        required=True,
        default=fields.Date.today,
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError('La fecha desde no puede ser mayor a la fecha hasta.')

    def create_orders_by_date(self):
        company = self.env.company if self.env.company else self.env.user.company_id
        company.get_orders_by_date_tn(self.date_from, self.date_to)