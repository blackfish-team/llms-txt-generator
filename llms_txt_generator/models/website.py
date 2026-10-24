# -*- coding: utf-8 -*-
from odoo import models

# Website fields that change the content of llms.txt
LLMS_TXT_WEBSITE_FIELDS = {'domain', 'language_ids', 'default_lang_id', 'company_id', 'ecommerce_access'}


class Website(models.Model):
    _inherit = 'website'

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
