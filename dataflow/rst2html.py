"""
Convert a restructured text document to html.

Inline math markup can uses the *math* directive, or it can use latex
style *\$expression\$*.  Math is rendered using simple html and unicode,
not mathjax.
"""
import re
from docutils.core import publish_parts


def rst2html(rst):
    """
    Convert restructured text into simple html.
    """
    rst = replace_dollar(rst)
    parts = publish_parts(source=rst, writer_name='html')
    return parts['body']


_dollar = re.compile(r"(?:^|(?<=\s|[(]))[$]([^\n]*?)(?<![\\])[$](?:$|(?=\s|[.,;)\\]))")
_notdollar = re.compile(r"\\[$]")
def replace_dollar(content):
    """
    Convert dollar signs to inline math markup in rst.
    """
    content = _dollar.sub(r":math:`\1`",content)
    content = _notdollar.sub("$", content)
    return content
