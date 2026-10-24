# -*- coding: utf-8 -*-
import contextlib
import datetime
import re

from odoo import fields, http
from odoo.http import request

# Like sitemap.xml, the file is cached so the public route cannot be used
# to trigger a full scan of the website on every request. The cache is also
# cleared when listed content changes; this delay catches what does not go
# through a write, such as a scheduled page reaching its publishing date.
LLMS_TXT_CACHE_TIME = datetime.timedelta(hours=1)
# Seconds browsers and proxies may reuse the response before revalidating
LLMS_TXT_MAX_AGE = 300


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
        dom = website._llms_txt_cache_domain()
        cached = Attachment.search(dom, limit=1)
        if cached and fields.Datetime.now() - cached.create_date < LLMS_TXT_CACHE_TIME:
            # Regenerate below if the stored file is missing (e.g. filestore not restored)
            with contextlib.suppress(FileNotFoundError):
                return self._llms_txt_response(cached)

        Attachment.search(dom).unlink()
        attachment = Attachment.create({
            'name': 'llms.txt',
            'type': 'binary',
            'raw': self._llms_txt_content().encode(),
            'mimetype': 'text/plain',
            'res_model': 'website',
            'res_id': website.id,
        })
        return self._llms_txt_response(attachment)

    def _llms_txt_response(self, attachment):
        # Served like /web/content: ETag and Last-Modified let clients
        # revalidate with a 304, and anonymous responses can be cached by proxies
        stream = attachment._to_http_stream()
        stream.max_age = LLMS_TXT_MAX_AGE
        stream.public = request.env.user._is_public()
        return stream.get_response()

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
