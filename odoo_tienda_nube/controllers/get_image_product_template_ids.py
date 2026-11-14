# -*- coding: utf-8 -*-
import base64
import io
import logging

from odoo import http
from odoo.http import request
from PIL import Image

_logger = logging.getLogger(__name__)


def _guess_image_format(binary_data):
    """Formato de imagen detectado con PIL. Reemplaza a imghdr.what(),
    removido del stdlib en Python 3.13 (Odoo 20 admite 3.12–3.14)."""
    try:
        with io.BytesIO(binary_data) as buffer:
            image = Image.open(buffer)
            return (image.format or 'PNG').lower()
    except Exception:
        return 'png'


class PublicController(http.Controller):

    @http.route('/ati_tn_product_template_ids/<int:id>', type='http', auth='public')
    def serve_image(self, id, **kwargs):
        record = request.env['product.product'].sudo().browse(id)
        binary_data = base64.b64decode(record.image_1920)
        image_format = _guess_image_format(binary_data)

        headers = [('Content-Type', f'image/{image_format.lower()}')]
        return request.make_response(binary_data, headers)

    @http.route('/ati_tn_product_template_galery_ids/<int:id>', type='http', auth='public')
    def serve_image_galery(self, id, **kwargs):
        record = request.env['product.image.tn'].sudo().browse(id)
        binary_data = base64.b64decode(record.image_1920)
        image_format = _guess_image_format(binary_data)

        headers = [('Content-Type', f'image/{image_format.lower()}')]
        return request.make_response(binary_data, headers)
