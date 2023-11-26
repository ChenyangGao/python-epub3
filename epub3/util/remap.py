#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io>"
__all__ = ["remap_links"]


from itertools import chain
from posixpath import dirname, normpath, join as joinpath, relpath
from re import compile as re_compile
from typing import Final, Mapping
from urllib.parse import urlsplit, urlunsplit, quote, unquote


PAT_STRING: Final = r"'(?P<single>[^'\\]*(?:\\.[^'\\]*)*)'|" + r'"(?P<double>[^"\\]*(?:\\.[^"\\]*)*)"'
CRE_REF: Final = re_compile(r'<[^/][^>]*?[\s:](?:href|src)=(?:%s)' % PAT_STRING)
CRE_CSS_URL: Final = re_compile(r'\burl\(\s*(?:%s|(?P<bare>[^)]*))\s*\)' % PAT_STRING)
CRE_STYLE_ATTR: Final = re_compile(r'<[^/][^>]*?\sstyle=(?:%s)' % PAT_STRING)
CRE_STYLE_ELEMENT: Final = re_compile(r'<style(?:\s[^>]*|)>(?P<value>(?s:.+?))</style>')
LINK_PATTERNS: Final = [
    ("text/css", CRE_CSS_URL), 
    ("application/x-dtbncx+xml", CRE_REF), 
    (("text/html", "application/xhtml+xml"), [
        CRE_REF, 
        (CRE_STYLE_ATTR, CRE_CSS_URL), 
        (CRE_STYLE_ELEMENT, CRE_CSS_URL)
    ]),
]


def chain_finditer(text, cres):
    try:
        yield from cres.finditer(text)
        return
    except AttributeError:
        pass
    if not cres:
        return
    it = cres[0].finditer(text)
    if len(cres) == 1:
        yield from it
        return
    stack = [it]
    top = len(cres) - 1
    i = 1
    while i:
        try:
            match = next(it)
        except StopIteration:
            it = stack.pop()
            i -= 1
        else:
            if i == top:
                yield from cres[i].finditer(text, *match.span(match.lastgroup))
            else:
                it = cres[i].finditer(text, *match.span(match.lastgroup))
                stack.append(it)
                i += 1


def path_repl_iter(matches, pathmap, basedir=""):
    if basedir:
        abspath = lambda path: normpath(joinpath(basedir, path))
    else:
        abspath = lambda path: path
    if isinstance(pathmap, Mapping):
        check = pathmap.__contains__
        if basedir:
            getnew = lambda path: relpath(pathmap[path], basedir)
        else:
            getnew = pathmap.__getitem__
    else:
        pathold, pathnew = pathmap
        check = pathold.__eq__
        if basedir:
            pathnew = relpath(pathnew, basedir)
        getnew = lambda path: pathnew
    for match in matches:
        path = unquote(match[match.lastgroup])
        urlp = urlsplit(path)
        if urlp.scheme or urlp.netloc:
            continue
        path = abspath(urlp.path)
        if check(path):
            pathnew = getnew(path)
            yield (
                match.span(match.lastgroup), 
                quote(urlunsplit(urlp._replace(path=pathnew)), safe=":/?&=#"), 
            )


def apply_repl_iter(text, repl_iter):
    start = 0
    for (begin, end), repl in repl_iter:
        yield text[start:begin]
        yield repl
        start = end
    yield text[start:]


def remap_links(
    manifest, 
    pathmap, 
    encoding="utf-8", 
    link_patterns=LINK_PATTERNS, 
):
    changed = []
    for predicate, patterns in link_patterns:
        for item in manifest.filter_by_attr(predicate):
            try:
                text = item.read_text(encoding=encoding)
                href = unquote(item["href"])
                basedir = dirname(href)
                if type(patterns) is list:
                    ls = []
                    for subpats in patterns:
                        repls = list(path_repl_iter(chain_finditer(text, subpats), pathmap, basedir))
                        if repls:
                            ls.append(repls)
                    if not ls:
                        repls = None
                    elif len(ls) > 1:
                        repls = sorted(chain.from_iterable(ls))
                    else:
                        repls = ls[0]
                else:
                    repls = list(path_repl_iter(chain_finditer(text, patterns), pathmap, basedir))
                if repls:
                    text = "".join(apply_repl_iter(text, repls))
                    item.write_text(text, encoding=encoding)
                changed.append(href)
            except:
                pass
    return changed

