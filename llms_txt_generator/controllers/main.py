# -*- coding: utf-8 -*-
import contextlib
import datetime
import re
import textwrap

from odoo import fields, http
from odoo.http import request
from odoo.tools.mail import html_to_inner_content

# Like sitemap.xml, the file is cached so the public route cannot be used
# to trigger a full scan of the website on every request. The cache is also
# cleared when listed content changes; this delay catches what does not go
# through a write, such as a scheduled page reaching its publishing date.
LLMS_TXT_CACHE_TIME = datetime.timedelta(hours=1)
# Seconds browsers and proxies may reuse the response before revalidating
LLMS_TXT_MAX_AGE = 300
# Longest description shown after a link
LLMS_TXT_NOTE_LENGTH = 200


def _md_text(text):
    """Collapse whitespace and escape Markdown link delimiters, so a record
    name cannot break out of its list item."""
    return re.sub(r'([\\\[\]])', r'\\\1', ' '.join(text.split()))


# Lines Markdown reads as headings: "#" or a setext "===" / "---" underline
_MD_HEADING_RE = re.compile(r'^(\s*)(#|=+\s*$|-+\s*$)')


def _md_block(text):
    """Escape headings in free text, as the format reserves them for its own
    structure (the H1 title and the H2 file lists)."""
    return "\n".join(_MD_HEADING_RE.sub(r'\1\\\2', line.rstrip()) for line in text.strip().splitlines())


def _llms_txt_note(record, field_names):
    """First non-empty description among field_names, shortened to one line."""
    for name in field_names:
        value = record[name]
        if value and record._fields[name].type == 'html':
            value = html_to_inner_content(value)
        if value and value.strip():
            return textwrap.shorten(value, LLMS_TXT_NOTE_LENGTH, placeholder="...")
    return ""


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
        now = fields.Datetime.now()

        # Header, in the order of the llmstxt.org format: H1 with the site
        # name, then a summary quote and free details
        blocks = [f"# {_md_text(website.llms_txt_title or website.name)}"]
        summary = website.llms_txt_summary
        if not summary:
            # Default to the homepage SEO description, in the website language
            home = website._get_website_pages([('url', '=', website.homepage_url or '/')])[:1]
            summary = home.with_context(lang=website.default_lang_id.code).website_meta_description
        if summary:
            blocks.append("\n".join(
                f"> {line}".rstrip() for line in _md_block(summary).splitlines()
            ))
        if website.llms_txt_details:
            blocks.append(_md_block(website.llms_txt_details))

        # File lists, as (mode, heading, records, label, fields to describe each link)
        sections = []

        # === Pages Section ===
        # Same filters as the sitemap: skip non-indexed, protected and scheduled pages
        if website.llms_txt_pages != 'exclude':
            pages = website._get_website_pages([
                ('website_published', '=', True),
                ('website_indexed', '=', True),
                ('visibility', '=', False),
                '|', ('date_publish', '=', False), ('date_publish', '<=', now),
            ])
            sections.append((website.llms_txt_pages, "Pages", pages, "Web page",
                             ['website_meta_description']))

        # === Blog Posts Section (only if Blog installed) ===
        if website.llms_txt_blog != 'exclude' and 'blog.post' in env:
            posts = env['blog.post'].search([
                ('website_published', '=', True),
                ('post_date', '<=', now),
            ])
            sections.append((website.llms_txt_blog, "Blog Posts", posts, "Blog post",
                             ['website_meta_description', 'subtitle', 'teaser']))

        # === Products Section (only if eCommerce installed and open to visitors) ===
        if (website.llms_txt_products != 'exclude' and hasattr(website, 'sale_product_domain')
                and website.has_ecommerce_access()):
            products = env['product.template'].search(website.sale_product_domain())
            sections.append((website.llms_txt_products, "Products", products, "Product page",
                             ['website_meta_description', 'description_sale', 'description_ecommerce']))

        # Links agents can skip when they need a shorter context
        optional = []
        for mode, heading, records, label, note_fields in sections:
            links = list(self._llms_txt_links(website, records, label, note_fields))
            if mode == 'optional':
                optional += links
            elif links:
                blocks.append("\n".join([f"## {heading}", *links]))

        # === Attribution ===
        optional.append("- [Clevacat](https://cleva.cat): Generated automatically by Clevacat")
        blocks.append("\n".join(["## Optional", *optional]))

        return "\n\n".join(blocks) + "\n"

    def _llms_txt_links(self, website, records, label, note_fields):
        base_url = website.get_base_url()
        default_lang = website.default_lang_id
        for record in records:
            for lang in website.language_ids:
                # URLs hold translated slugs, so read everything in the link language
                record_lang = record.with_context(lang=lang.code)
                url = record_lang.website_url
                if lang != default_lang:
                    url = f"/{lang.url_code}{url if url != '/' else ''}"
                title = record_lang.name or url
                note = _llms_txt_note(record_lang, note_fields) or f"{label} in {lang.code}"
                yield f"- [{_md_text(title)}]({base_url}{url}): {_md_text(note)}"
