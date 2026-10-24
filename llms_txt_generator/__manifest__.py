{
    'name': "LLMS.txt Generator",
    'summary': "Generate an llms.txt file for SEO and LLM-friendly indexing in Odoo websites",
    'description': """
LLMS TXT Generator for Odoo
===========================

This module generates an **llms.txt** file automatically, following the [llmstxt.org](https://llmstxt.org/) guidelines.
The file improves **SEO** and helps **large language models (LLMs)** better understand your site content.

Key Features:
- Published Pages, Blog Posts, and eCommerce Products (if available)
- Multi-language support
- Title, summary and details configurable per website, and per-section choice to list, mark as Optional or leave out
- Links described with their SEO descriptions, or blog subtitles and product descriptions
- Fully compliant with llmstxt.org specifications
- Configurable attribution backlink

About Clevacat:
---------------
Clevacat helps SMEs turn data into competitive advantage through predictive modeling, object detection,
conversational AI, and business automation. Drive digital transformation with practical AI solutions that deliver measurable results.

Learn more: https://cleva.cat
    """,
    'author': "Clevacat",
    'website': "https://cleva.cat",
    'category': 'Website/SEO',
    'version': '1.1',
    'depends': ['website'],
    'data': [
        'data/llms_txt_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
