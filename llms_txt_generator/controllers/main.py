# -*- coding: utf-8 -*-
import datetime
import re

from odoo import fields, http
from odoo.http import request

# Like sitemap.xml, the file is cached so the public route cannot be used
# to trigger a full scan of the website on every request.
LLMS_TXT_CACHE_TIME = datetime.timedelta(hours=1)


def _md_text(text):
    """Collapse whitespace and escape Markdown link delimiters, so a record
    name cannot break out of its list item."""
    return re.sub(r'([\\\[\]])', r'\\\1', ' '.join(text.split()))


class LlmsTxtController(http.Controller):

    @http.route('/llms.txt', type='http', auth="public", website=True,
                multilang=False, sitemap=False, methods=['GET'])
    def llms_txt(self):
        website = request.website
        Attachment = request.env['ir.attachment'].sudo()
        dom = [
            ('res_model', '=', 'website'), ('res_id', '=', website.id),
            ('name', '=', 'llms.txt'), ('type', '=', 'binary'),
        ]
        content = None
        cached = Attachment.search(dom, limit=1)
        if cached and fields.Datetime.now() - cached.create_date < LLMS_TXT_CACHE_TIME:
            content = cached.raw
        # Also regenerate when the stored file is missing (e.g. filestore not restored)
        if not content:
            Attachment.search(dom).unlink()
            content = self._llms_txt_content().encode()
            Attachment.create({
                'name': 'llms.txt',
                'type': 'binary',
                'raw': content,
                'mimetype': 'text/plain',
                'res_model': 'website',
                'res_id': website.id,
            })

        # Return plain text response
        return request.make_response(
            content,
            headers=[('Content-Type', 'text/plain; charset=utf-8')]
        )

    def _llms_txt_content(self):
        # Generate as the website's public user, so access rules apply and the
        # cached file never depends on who requested it.
        website = request.website.with_user(request.website.user_id).with_context(
            allowed_company_ids=request.website.company_id.ids,
        )
        env = website.env
        base_url = website.get_base_url()
        now = fields.Datetime.now()

        content = [
            "# LLM-Friendly Site Map",
            "# Following the llmstxt.org guidelines",
            f"# Base URL: {base_url}",
            "",
        ]

        # === Pages Section ===
        # Same filters as the sitemap: skip non-indexed, protected and scheduled pages
        pages = website._get_website_pages([
            ('website_published', '=', True),
            ('website_indexed', '=', True),
            ('visibility', '=', False),
            '|', ('date_publish', '=', False), ('date_publish', '<=', now),
        ])
        if pages:
            content.append("## Pages")
            content.extend(self._llms_txt_links(website, pages, "Web page"))

        # === Blog Posts Section (only if Blog installed) ===
        if 'blog.post' in env:
            posts = env['blog.post'].search([
                ('website_published', '=', True),
                ('post_date', '<=', now),
            ])
            if posts:
                content.append("\n## Blog Posts")
                content.extend(self._llms_txt_links(website, posts, "Blog post"))

        # === Products Section (only if eCommerce installed and open to visitors) ===
        if hasattr(website, 'sale_product_domain') and website.has_ecommerce_access():
            products = env['product.template'].search(website.sale_product_domain())
            if products:
                content.append("\n## Products")
                content.extend(self._llms_txt_links(website, products, "Product page"))

        # === Attribution Section ===
        content.append("\n## Attribution")
        content.append(
            "Generated automatically by Clevacat - https://cleva.cat"
        )

        return "\n".join(content)

    def _llms_txt_links(self, website, records, label):
        base_url = website.get_base_url()
        default_lang = website.default_lang_id
        for record in records:
            for lang in website.language_ids:
                url = record.website_url
                if lang != default_lang:
                    url = f"/{lang.url_code}{url if url != '/' else ''}"
                title = record.with_context(lang=lang.code).name or url
                yield f"- [{_md_text(title)}]({base_url}{url}): {label} in {lang.code}"
