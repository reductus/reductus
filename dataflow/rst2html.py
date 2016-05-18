"""
Convert a restructured text document to html.

Inline math markup can uses the *math* directive, or it can use latex
style *\$expression\$*.  Math is rendered using simple html and unicode,
not mathjax.
"""
import re
from docutils.core import publish_parts


def rst2html(rst, part='html_body'):
    """
    Convert restructured text into simple html.

    The following parts are available:

        whole: the entire html document

        html_body: document division with title and contents and footer

        body: contents only

    There are other parts, but they don't make sense alone:

        subtitle, version, encoding, html_prolog, header, meta,
        html_title, title, stylesheet, html_subtitle, html_body,
        body, head, body_suffix, fragment, docinfo, html_head,
        head_prefix, body_prefix, footer, body_pre_docinfo, whole

    """
    rst = replace_dollar(rst)
    parts = publish_parts(source=rst, writer_name='html')
    return parts[part]


_dollar = re.compile(r"(?:^|(?<=\s|[(]))[$]([^\n]*?)(?<![\\])[$](?:$|(?=\s|[.,;)\\]))")
_notdollar = re.compile(r"\\[$]")
def replace_dollar(content):
    """
    Convert dollar signs to inline math markup in rst.
    """
    content = _dollar.sub(r":math:`\1`",content)
    content = _notdollar.sub("$", content)
    return content
