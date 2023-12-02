#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io>"
__all__ = [
    "make_container_xml", "make_opf", "make_html", "make_xhtml", "make_nav_xhtml"]


from datetime import datetime
from html import escape
from typing import Mapping, Optional
from urllib.parse import quote
from uuid import uuid4

from .helper import items


def _make_tag(
    name: str, 
    attrs: Optional[Mapping] = None, 
    indent: int = 0, 
) -> str:
    return '%s<%s%s>' % (
        " " * indent, 
        name, 
        "".join(
            ' %s="%s"' % (k, str(v).replace('"', '&quot;')) 
            for k, v in items(attrs)
        ) if attrs else ""
    )


def make_container_xml(
    rootfile: str = "OEBPS/content.opf", 
    /, 
    *rootfiles: str, 
) -> str:
    return '''\
<?xml version="1.0" encoding="utf-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
''' + ("\n".join(
    '    <rootfile media-type="application/oebps-package+xml" full-path="%s" />' % quote(rootfile, safe=b":/?&=#")
    for rootfile in (rootfile, *rootfiles)
) if rootfiles else (
    '    <rootfile media-type="application/oebps-package+xml" full-path="%s" />' % quote(rootfile, safe=b":/?&=#")
)) + '''
  </rootfiles>
</container>'''


def make_opf(identifier: str = "", language="en", title=""):
    if not identifier:
        identifier = f"urn:uuid:{uuid4()}"
    return f'''\
<?xml version="1.0" encoding="utf-8"?>
<package version="3.0" unique-identifier="BookId" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="BookId">{escape(identifier)}</dc:identifier>
    <dc:language>{escape(language)}</dc:language>
    <dc:title>{escape(title)}</dc:title>
    <meta property="dcterms:modified">{datetime.now().strftime("%FT%XZ")}</meta>
  </metadata>
  <manifest />
  <spine />
</package>'''


def make_html(
    title: Optional[str] = "", 
    html_attrs: Optional[Mapping] = None, 
    head_attrs: Optional[Mapping] = None, 
    head_html: Optional[str] = None, 
    body_attrs: Optional[Mapping] = None, 
    body_html: Optional[str] = None, 
):
    parts: list[str] = []
    add_part = parts.append
    add_part('<!DOCTYPE html>')
    add_part(_make_tag("html", html_attrs))
    add_part(_make_tag("head", head_attrs, 2))
    if title is not None:
        add_part(f'    <title>{escape(title)}</title>')
    if head_html is None:
        add_part('    <meta charset="utf-8" />')
    elif head_html:
        add_part(head_html)
    add_part('  </head>')
    add_part(_make_tag("body", body_attrs, 2))
    if body_html:
        add_part(body_html)
    add_part('  </body>')
    add_part('</html>')
    return "\n".join(parts)


def make_xhtml(
    title: Optional[str] = "", 
    html_attrs: Optional[Mapping] = None, 
    head_attrs: Optional[Mapping] = None, 
    head_html: Optional[str] = None, 
    body_attrs: Optional[Mapping] = None, 
    body_html: Optional[str] = None, 
):
    if html_attrs is None:
        html_attrs = {}
    else:
        html_attrs = dict(html_attrs)
    html_attrs.setdefault("xmlns", "http://www.w3.org/1999/xhtml")
    html_attrs.setdefault("xmlns:epub", "http://www.idpf.org/2007/ops")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + make_html(
        title, html_attrs, head_attrs, head_html, body_attrs, body_html
    )


def make_nav_xhtml(
    title: Optional[str] = "ePub NAV", 
    html_attrs: Optional[Mapping] = None, 
    head_attrs: Optional[Mapping] = None, 
    head_html: Optional[str] = None, 
    body_attrs: Optional[Mapping] = None, 
    body_html: Optional[str] = None, 
):
    if body_attrs is None:
        body_attrs = {}
    else:
        body_attrs = dict(body_attrs)
    body_attrs.setdefault("epub:type", "frontmatter")
    if body_html is None:
        body_html = '''\
  <nav epub:type="toc" id="toc" role="doc-toc">
    <h1>Table of Contents</h1>
  </nav>
  <nav epub:type="landmarks" id="landmarks" hidden="">
    <h1>Landmarks</h1>
    <ol>
      <li>
        <a epub:type="toc" href="#toc">Table of Contents</a>
      </li>
    </ol>
  </nav>'''
    return make_xhtml(
        title, html_attrs, head_attrs, head_html, body_attrs, body_html
    )


def make_link():
    '<link href="../Styles/sgc-nav.css" rel="stylesheet" type="text/css"/>'


# 允许指定: html items=() (自动构建link append to head)
# 参考这个：https://docs.sourcefabric.org/projects/ebooklib/en/latest/_modules/ebooklib/epub.html#EpubHtml.get_content

# 这个并不实际需要，而是注入上面xhtml的模板函数
# 参考 ebooklib, Epubwriter.def _get_nav(self, item)方法和def _get_ncx(self)

