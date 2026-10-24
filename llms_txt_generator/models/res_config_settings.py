# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    llms_txt_title = fields.Char(related='website_id.llms_txt_title', readonly=False)
    llms_txt_summary = fields.Text(related='website_id.llms_txt_summary', readonly=False)
    llms_txt_details = fields.Text(related='website_id.llms_txt_details', readonly=False)
    llms_txt_pages = fields.Selection(related='website_id.llms_txt_pages', readonly=False)
    llms_txt_blog = fields.Selection(related='website_id.llms_txt_blog', readonly=False)
    llms_txt_products = fields.Selection(related='website_id.llms_txt_products', readonly=False)
    llms_txt_has_blog = fields.Boolean(compute='_compute_llms_txt_has_apps')
    llms_txt_has_shop = fields.Boolean(compute='_compute_llms_txt_has_apps')

    def _compute_llms_txt_has_apps(self):
        # Blog and eCommerce are optional, only show their options when installed
        has_blog = 'blog.post' in self.env
        has_shop = hasattr(self.env['website'], 'sale_product_domain')
        for settings in self:
            settings.llms_txt_has_blog = has_blog
            settings.llms_txt_has_shop = has_shop
