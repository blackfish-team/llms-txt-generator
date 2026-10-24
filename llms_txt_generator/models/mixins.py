# -*- coding: utf-8 -*-
from odoo import api, models

# Models listed in llms.txt (all inherit this mixin), and the fields that
# change their entry
LLMS_TXT_MODELS = {'website.page', 'blog.post', 'product.template'}
LLMS_TXT_FIELDS = {
    'name', 'active', 'is_published', 'website_published', 'website_id', 'website_meta_description',
    # website.page
    'url', 'visibility', 'website_indexed', 'date_publish',
    # blog.post
    'blog_id', 'published_date', 'post_date', 'subtitle', 'teaser', 'teaser_manual', 'content',
    # product.template
    'sale_ok', 'company_id', 'service_tracking', 'description_sale', 'description_ecommerce',
}


class WebsitePublishedMultiMixin(models.AbstractModel):
    _inherit = 'website.published.multi.mixin'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self._name in LLMS_TXT_MODELS:
            self.env['website']._llms_txt_clear_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self._name in LLMS_TXT_MODELS and not LLMS_TXT_FIELDS.isdisjoint(vals):
            self.env['website']._llms_txt_clear_cache()
        return res

    def unlink(self):
        if self._name in LLMS_TXT_MODELS:
            self.env['website']._llms_txt_clear_cache()
        return super().unlink()
