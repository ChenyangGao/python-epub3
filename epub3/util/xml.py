#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io>"
__all__ = [
    "generalize_elementpath", "generalize_xpath", "clean_nsmap", "extract_name", 
    "resolve_prefix", "el_find", "el_iterfind", "el_xpath", "el_add", "el_del", 
    "el_set", "el_setfind", 
]

from itertools import chain, pairwise
from re import compile as re_compile, Match, Pattern
from typing import cast, Callable, Final, ItemsView, Iterable, Iterator, Mapping, NamedTuple, Optional
try:
    # https://lxml.de
    from lxml.etree import _Element as Element # type: ignore
    from lxml._elementpath import xpath_tokenizer_re # type: ignore
    USE_BUILTIN_XML = False
except ModuleNotFoundError:
    # https://docs.python.org/3/library/xml.etree.elementtree.html
    from xml.etree.ElementTree import Element # type: ignore
    from xml.etree.ElementPath import xpath_tokenizer_re # type: ignore
    USE_BUILTIN_XML = True

from .helper import get, items
from .undefined import undefined


XPATH_TOEKN_PATS: Final = [
    ("DSLASH", r"//"), 
    ("SLASH", r"/"), 
    ("LBRACKET", r"\["), 
    ("RBRACKET", r"\]"), 
    ("LPARAN", r"\("), 
    ("RPARAN", r"\)"), 
    ("DCOLON", r"::"), 
    ("COLON", r":"), 
    ("DDOT", r"\.\."), 
    ("DOT", r"\."), 
    ("AT", r"@"), 
    ("DOLLAR", "\$"), 
    ("COMMA", r","), 
    ("STAR", r"\*"), 
    ("VERTICAL_BAR", r"\|"), 
    ("QM", r"\?"), 
    ("COMP", r"!=|<=|>=|=|<|="), 
    ("NUMBER", r"\d+(?:\.\d*)?|\.\d+"), 
    ("NAME", r"\w[\w.-]*"), 
    ("STRING", r"'[^'\\]*(?:\\.[^'\\]*)*'|" + r'"[^"\\]*(?:\\.[^"\\]*)*"'),
    ("WHITESPACES", r"\s+"), 
    ("ANY", r"(?s:.)"), 
]
CRE_XPATH_TOKEN: Final = re_compile("|".join("(?P<%s>%s)" % pair for pair in XPATH_TOEKN_PATS))
ELEMENTPATH_TOEKN_PATS: Final = [
    ("DSLASH", r"//"), 
    ("SLASH", r"/"), 
    ("LBRACKET", r"\["), 
    ("RBRACKET", r"\]"), 
    ("LPARAN", r"\("), 
    ("RPARAN", r"\)"), 
    ("COLON", r":"), 
    ("DDOT", r"\.\."), 
    ("DOT", r"\."), 
    ("AT", r"@"), 
    ("STAR", r"\*"), 
    ("COMP", r"!=|="), 
    ("NUMBER", r"\d+"), 
    ("NAME", r"\w[\w.-]*"), 
    ("STRING", r"'[^'\\]*(?:\\.[^'\\]*)*'|" + r'"[^"\\]*(?:\\.[^"\\]*)*"'), 
    ("NSURI", r"\{[^}]*\}"), 
    ("WHITESPACES", r"\s+"), 
    ("ANY", r"(?s:.)"), 
]
CRE_ELEMENTPATH_TOKEN: Final = re_compile("|".join("(?P<%s>%s)" % pair for pair in ELEMENTPATH_TOEKN_PATS))


class Token(NamedTuple):
    type: str
    value: str
    start: int
    stop: int
    match: Match


def tokenize(
    xpath: str, 
    tokenspec: Pattern = CRE_XPATH_TOKEN, 
) -> Iterator[Token]:
    """
    """
    # Reference:
    #   - https://www.python.org/community/sigs/retired/parser-sig/towards-standard/
    #   - https://www.w3.org/TR/xpath/
    #   - https://github.com/antlr/antlr4
    #   - https://www.gnu.org/software/bison/
    #   - https://www.antlr3.org/grammar/list.html
    #   - https://github.com/antlr/grammars-v4/tree/master/xpath
    #   - https://github.com/lark-parser/lark
    #   - https://github.com/dabeaz/ply
    for match in tokenspec.finditer(xpath):
        token_type = cast(str, match.lastgroup)
        token_value = match.group(token_type)
        yield Token(token_type, token_value, *match.span(), match)


def name_token_iter(
    path: str, 
    /, 
    tokenspec: Pattern = CRE_XPATH_TOKEN, 
) -> Iterator[Token]:
    """
    """
    step_begin = True
    pred_level = 0
    #para_level = 0
    cache_token = None
    for token in tokenize(path, tokenspec):
        type = token.type
        value = token.value
        if type == "WHITESPACES":
            continue
        if step_begin:
            if type == "NAME":
                cache_token = token
                continue
            # NOTE: axes end
            elif type == "DCOLON":
                if cache_token:
                    cache_token = None
                else:
                    step_begin = False
                continue
        if not pred_level and type in ("SLASH", "DSLASH", "VERTICAL_BAR"):
            if cache_token:
                yield cache_token
                cache_token = None
            step_begin = True
            continue
        if cache_token:
            if not pred_level and type == "LBRACKET":
                yield cache_token
            cache_token = None
        if type == "LBRACKET":
            pred_level += 1
        elif type == "RBRACKET" and pred_level:
            pred_level -= 1
        step_begin = False
    if cache_token:
        yield cache_token


def generalize_elementpath(
    epath: str, 
    /, 
    prefix: Optional[str] = None, 
    uri: Optional[str] = None, 
) -> str:
    """Generalizes a given ElementPath expression, so that namespaces can be disregarded or determined. 

    :param epath: The original ElementPath to be generalized.
    :param prefix: An optional prefix for the generalized version.
    :param uri: An optional URI for the generalized version.

    :return: The generalized ElementPath.

    :NOTE:

        - The `prefix` takes precedence over the `uri`.
        - `prefix` takes effect when `prefix` is a non-empty string.
        - `uri` takes effect when `prefix` is None and `uri` is a string.

    :EXAMPLE:

        >>> generalize_elementpath("title")
        '{*}title'
        >>> generalize_elementpath("title", "dc")
        'dc:title'
        >>> generalize_elementpath("title", uri="http://purl.org/dc/elements/1.1/")
        '{http://purl.org/dc/elements/1.1/}title'
        >>> generalize_elementpath("title", uri="")
        '{}title'
    """
    tokens = tuple(name_token_iter(epath, CRE_ELEMENTPATH_TOKEN))
    if not tokens:
        return epath
    parts: list[str] = []
    add_part = parts.append
    if prefix:
        expand = f"{prefix}:%s".__mod__
    elif uri is not None:
        expand = f"{{{uri}}}%s".__mod__
    else:
        expand = '{*}%s'.__mod__
    start = 0
    for token in tokens:
        add_part(epath[start:token.start])
        add_part(expand(token.value))
        start = token.stop
    add_part(epath[start:])
    return "".join(parts)


def generalize_xpath(
    xpath: str, 
    /, 
    prefix: Optional[str] = None, 
) -> str:
    """Generalizes a given XPath expression, so that namespaces can be disregarded or determined. 

    :param xpath: The XPath expression to be generalized.
    :param prefix: An optional namespace prefix to be used in the generalized XPath.
                   If provided, the prefix is added before the tag names in the XPath.
                   If not provided, the 'local-name()' function is used to match the tag names in the XPath.

    :return: The generalized XPath.

    :EXAMPLE:

        >>> generalize_xpath("element")
        '*[local-name()="element"]'
        >>> generalize_elementpath("element", "xml")
        'xml:element'
    """
    # TODO: Research is ongoing for XPath of more complex nested structures, even XSLT.
    tokens = tuple(name_token_iter(xpath, CRE_XPATH_TOKEN))
    if not tokens:
        return xpath
    parts: list[str] = []
    add_part = parts.append
    if prefix:
        expand = f"{prefix}:%s".__mod__
    else:
        expand = '*[local-name()="%s"]'.__mod__
    start = 0
    for token in tokens:
        add_part(xpath[start:token.start])
        add_part(expand(token.value))
        start = token.stop
    add_part(xpath[start:])
    return "".join(parts)


def clean_nsmap(
    nsmap: Mapping, 
    extra_nsmap: Optional[Mapping] = None, 
    predicate_key: Optional[Callable] = None, 
    predicate_value: Callable = bool, 
) -> Mapping:
    """Build a clean dictionary from a given `nsmap` and an optional `extra_nsmap`.

    :param nsmap: The namespace map object to be cleaned. It can be a mapping object or 
                  an iterable of key-value pairs representing namespaces.
    :param extra_nsmap: An additional namespace map object to be merged with the nsmap.
    :param predicate_key: 
        A callable that takes a key as input and returns a boolean value. 
        If provided, only entries with keys that satisfy the predicate will be included in the cleaned dictionary.
    :param predicate_value: 
        A callable that takes a value as input and returns a boolean value. 
        If provided, only entries with values that satisfy the predicate will be included in the cleaned dictionary.

    :return: A cleaned namespace map as a dictionary.
    """
    if nsmap:
        pairs = items(nsmap)
        if extra_nsmap:
            pairs = chain(pairs, items(extra_nsmap))
    elif extra_nsmap:
        pairs = items(extra_nsmap)
    else:
        return nsmap
    if predicate_key is None:
        return {k: v for k, v in pairs if predicate_value(v)}
    return {k: v for k, v in pairs if predicate_key(k) and predicate_value(v)}


def extract_name(
    path: str, 
    /, 
    _match_name=re_compile(r"\w(?<!\d)[\w.-]*").match, 
    _match_prefix_name=re_compile(r"(?:(?:\w(?<!\d)[\w.-]*)?:)?\w(?<!\d)[\w.-]*").match, 
) -> str:
    """
    """
    if path.startswith("{"):
        end = path.find("}")
        if end == -1:
            return ""
        uri = path[1:end]
        match = _match_name(path, end+1)
        if match is None:
            return ""
        return path[:match.end()]
    match = _match_prefix_name(path)
    if match is None:
        return ""
    return match[0]


def resolve_prefix(
    name: str, 
    nsmap: Optional[Mapping] = None, 
    optional_nsmap: Optional[Mapping] = None, 
    inherit: bool = False, 
    _match=re_compile(r"\w(?<!\d)[\w.-]*:").match, 
) -> str:
    """
    """
    if not name:
        return name
    elif name.startswith(":"):
        return name.lstrip(":")
    elif name.startswith("{}"):
        return name.removeprefix("{}")
    elif name.startswith("{*}"):
        name = name.removeprefix("{*}")
        inherit = True
    elif name.startswith("{"):
        return name
    if not nsmap and not optional_nsmap:
        return name
    prefix = _match(name)
    uri = ""
    if prefix is None:
        if not inherit:
            return name
        if nsmap:
            uri = get(nsmap, None) or get(nsmap, "")
        if not uri and optional_nsmap:
            uri = get(optional_nsmap, None) or get(optional_nsmap, "")
        name0 = name
    else:
        index = prefix.end()
        prefix, name0 = name[:index-1], name[index:]
        if nsmap:
            uri = get(nsmap, prefix)
        if not uri and optional_nsmap:
            uri = get(optional_nsmap, prefix)
    if not uri:
        return name
    return f"{{{uri}}}{name0}"


def _el_set(
    el: Element, 
    /, 
    attrib: Optional[Mapping] = None, 
    text=None, 
    tail=None, 
    nsmap: Optional[Mapping] = None, 
    optional_nsmap: Optional[Mapping] = None, 
):
    """
    """
    if attrib:
        el_attrib = el.attrib
        for key, val in items(attrib):
            if key == "":
                el.text = val if val is None else str(val)
            elif key is None:
                el.tail = val if val is None else str(val)
            elif isinstance(key, str) and key != "xmlns" and not key.startswith("xmlns:"):
                key = resolve_prefix(key, nsmap, optional_nsmap)
                if val is None:
                    el_attrib.pop(key, "")
                el_attrib[key] = str(val)
    if callable(text):
        text = text()
        if text is None:
            el.text = None
    if text is not None:
        el.text = str(text)
    if callable(tail):
        tail = tail()
        if tail is None:
            el.tail = None
    if tail is not None:
        el.tail = str(tail)


def _el_setmerge(
    el: Element, 
    /, 
    attrib: Optional[Mapping] = None, 
    text=None, 
    tail=None, 
    nsmap: Optional[Mapping] = None, 
    optional_nsmap: Optional[Mapping] = None, 
):
    """
    """
    if attrib:
        el_attrib = el.attrib
        for key, val in items(attrib):
            if val is None:
                continue
            if key == "":
                if el.text is None:
                    el.text = str(val)
            elif key is None:
                if el.tail is None:
                    el.tail = str(val)
            elif isinstance(key, str) and key != "xmlns" and not key.startswith("xmlns:"):
                key = resolve_prefix(key, nsmap, optional_nsmap)
                if key not in el_attrib:
                    el_attrib[key] = val
    if el.text is None:
        if callable(text):
            text = text()
            if text is None:
                pass
        if text is not None:
            el.text = str(text)
    if el.tail is None:
        if callable(tail):
            tail = tail()
            if tail is None:
                pass
        if tail is not None:
            el.tail = str(tail)


def el_find(
    el: Element, 
    path: Optional[str] = None, 
    /, 
    namespaces: Optional[Mapping] = None, 
) -> Optional[Element]:
    """
    """
    return next(el_iterfind(el, path, namespaces), None)


def el_iterfind(
    el: Element, 
    path: Optional[str] = None, 
    /, 
    namespaces: Optional[Mapping] = None, 
) -> Iterator[Element]:
    """
    """
    if not path or path in (".", "*..", "*...", "./."):
        return iter((el,))
    nsmap: Optional[Mapping]
    if USE_BUILTIN_XML:
        nsmap = namespaces
    else:
        nsmap = el.nsmap
        if namespaces:
            nsmap.update(namespaces)
    if nsmap and (None in nsmap or "" in nsmap):
        if any(
            l == "[" and r != "@" 
            for l, r in pairwise(m[0] for m in xpath_tokenizer_re.finditer(path))
        ):
            uri = get(nsmap, None) or get(nsmap, "") or "*"
            path = generalize_elementpath(path, uri=uri)
            nsmap = {k: v for k, v in items(nsmap) if k and v}
    return el.iterfind(path, nsmap) # type: ignore


def el_xpath(
    el: Element, 
    path: Optional[str] = None, 
    /, 
    namespaces: Optional[Mapping] = None, 
    **kwargs, 
) -> list:
    """
    """
    if not path or path == ".":
        return [el]
    nsmap: Optional[Mapping]
    try:
        nsmap = el.nsmap # type: ignore
    except:
        nsmap = namespaces
    else:
        if nsmap:
            nsmap = {k: v for k, v in nsmap.items() if k and v}
        if namespaces:
            nsmap.update(namespaces)
    return el.xpath(path, namespaces=nsmap, **kwargs) # type: ignore


def el_add(
    el: Element, 
    /, 
    name: str, 
    attrib: Optional[Mapping] = None, 
    text=None, 
    tail=None, 
    namespaces: Optional[Mapping] = None, 
) -> Element:
    """
    """
    name = extract_name(name)
    if not name:
        raise ValueError("unable to determine name")
    try:
        nsmap = el.nsmap # type: ignore
    except:
        nsmap = {}
    if attrib:
        attrib0 = items(attrib)
        attrib = {}
        for key, val in attrib0:
            if key is None:
                attrib[key] = val
            elif isinstance(key, str):
                if key == "xmlns":
                    if val:
                        nsmap[None] = val
                    else:
                        nsmap.pop(None, None)
                elif key.startswith("xmlns:"):
                    if val:
                        nsmap[key[6:]] = val
                    else:
                        nsmap.pop(key[6:], None)
                else:
                    attrib[key] = val
    name = resolve_prefix(name, nsmap, namespaces, inherit=True)
    if USE_BUILTIN_XML:
        sel = el.makeelement(name, cast(dict[str, str], {}))
    else:
        sel = el.makeelement(name, nsmap=cast(dict[str, str], nsmap))
    el.append(sel)
    _el_set(sel, attrib, text, tail, nsmap, namespaces)
    return sel


def el_del(
    el: Element, 
    path: Optional[str] = None, 
    /, 
    namespaces: Optional[Mapping] = None, 
) -> Optional[Element]:
    """
    """
    sel = el_find(el, path, namespaces) if path else el
    if sel is not None:
        try:
            pel = sel.getparent() # type: ignore
        except AttributeError:
            pel = el
        if pel is None or pel is sel:
            raise LookupError(f"can't get parent element: {sel!r}")
        pel.remove(sel)
    return sel


def el_set(
    el: Element, 
    path: Optional[str] = None, 
    /, 
    name: Optional[str] = None, 
    attrib: Optional[Mapping] = None, 
    text: Optional[str] = None, 
    tail: Optional[str] = None, 
    namespaces: Optional[Mapping] = None, 
    merge: bool = False, 
) -> Element:
    """
    """
    sel = el_find(el, path, namespaces) if path else el
    if sel is not None:
        if text is None and tail is None and not attrib:
            return sel
        try:
            nsmap = sel.nsmap # type: ignore
        except:
            nsmap = None
        (_el_setmerge if merge else _el_set)(sel, attrib, text, tail, nsmap, namespaces)
    elif name is not None:
        if name == "":
            name = path
        sel = el_add(el, cast(str, name), attrib=attrib, text=text, tail=tail, namespaces=namespaces)
    else:
        raise LookupError(f"element not found: {el!r}.find({path!r}) is None")
    return sel


def el_setfind(
    el: Element, 
    /, 
    name: str, 
    find_attrib: Optional[Mapping] = None, 
    attrib: Optional[Mapping] = None, 
    text: Optional[str] = None, 
    tail: Optional[str] = None, 
    namespaces: Optional[Mapping] = None, 
    merge: bool = False, 
    delete: bool = False, 
    auto_add: bool = False, 
) -> Optional[Element]:
    """
    """
    find_text = find_tail = undefined
    no_keys = set()
    preds = name
    if find_attrib:
        pred_parts = []
        for key, val in items(find_attrib):
            if key is None:
                find_tail = val
            elif key == "":
                find_text = val
            elif val is None:
                no_keys.add(key)
            else:
                pred_parts.append((key, val))
        if pred_parts:
            preds += "".join("[@%s=%r]" % t for t in pred_parts)
    if find_text is undefined and find_tail is undefined and not no_keys:
        sel = el_find(el, preds, namespaces=namespaces)
    else:
        for sel in el_iterfind(el, preds, namespaces=namespaces):
            if (
                (find_text is undefined or sel.text == find_text) and 
                (find_tail is undefined or sel.tail == find_tail) and 
                not (no_keys and any(key in sel.attrib for key in no_keys))
            ):
                break
        else:
            sel = None
    if delete:
        if sel is not None:
            el.remove(sel)
    elif sel is None:
        if auto_add:
            if find_attrib:
                if attrib:
                    attrib = {**find_attrib, **attrib}
                else:
                    attrib = find_attrib
            sel = el_add(el, name, attrib=attrib, text=text, tail=tail, namespaces=namespaces)
    else:
        el_set(sel, attrib=attrib, text=text, tail=tail, namespaces=namespaces, merge=merge)
    return sel

