# -*- coding: utf-8 -*-
from odoo import fields, models

LLMS_TXT_SECTION_MODES = [
    ('include', "Include"),
    ('optional', "Include as Optional"),
    ('exclude', "Do not include"),
]

# Website fields that change the content of llms.txt
LLMS_TXT_WEBSITE_FIELDS = {
    'name', 'domain', 'language_ids', 'default_lang_id', 'company_id', 'ecommerce_access',
    'llms_txt_title', 'llms_txt_summary', 'llms_txt_details',
    'llms_txt_pages', 'llms_txt_blog', 'llms_txt_products',
}


class Website(models.Model):
    _inherit = 'website'

    llms_txt_title = fields.Char(
        "llms.txt Title",
        help="Name shown as the heading of /llms.txt. Defaults to the website name.")
    llms_txt_summary = fields.Text(
        "llms.txt Summary",
        help="Short summary of the website, shown as a quote below the heading.")
    llms_txt_details = fields.Text(
        "llms.txt Details",
        help="More detailed information about the website and how to read the listed links.")
    llms_txt_pages = fields.Selection(
        LLMS_TXT_SECTION_MODES, "llms.txt Pages", default='include', required=True)
    llms_txt_blog = fields.Selection(
        LLMS_TXT_SECTION_MODES, "llms.txt Blog Posts", default='include', required=True)
    llms_txt_products = fields.Selection(
        LLMS_TXT_SECTION_MODES, "llms.txt Products", default='include', required=True)

    def _llms_txt_cache_domain(self):
        """Domain of the cached llms.txt of these websites, or of every
        website when called on an empty recordset."""
        domain = [('res_model', '=', 'website'), ('name', '=', 'llms.txt'), ('type', '=', 'binary')]
        if self:
            domain.append(('res_id', 'in', self.ids))
        return domain

    def _llms_txt_clear_cache(self):
        self.env['ir.attachment'].sudo().search(self._llms_txt_cache_domain()).unlink()

    def write(self, vals):
        res = super().write(vals)
        if not LLMS_TXT_WEBSITE_FIELDS.isdisjoint(vals):
            self._llms_txt_clear_cache()
        return res
