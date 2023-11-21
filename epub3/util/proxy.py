#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__all__ = ["NAMESPACES", "ElementAttribProxy", "ElementProxy"]

from functools import cached_property
from inspect import isclass
from typing import Final, ItemsView, Mapping, MutableMapping
from types import MappingProxyType
from weakref import WeakKeyDictionary, WeakValueDictionary

try:
    from lxml.etree import SubElement, _Element as Element, _ElementTree as ElementTree # type: ignore
    USE_BUILTIN_XML = False
except ModuleNotFoundError:
    from xml.etree.ElementTree import SubElement, Element, ElementTree # type: ignore
    USE_BUILTIN_XML = True

from .helper import items
from .undefined import undefined
from .xml import el_add, el_del, el_iterfind, el_set, el_setfind, resolve_prefix


NAMESPACES: Final = {
    "xml": "http://www.w3.org/XML/1998/namespace", 
    "epub": "http://www.idpf.org/2007/ops", 
    "daisy": "http://www.daisy.org/z3986/2005/ncx/", 
    "opf": "http://www.idpf.org/2007/opf", 
    "containerns": "urn:oasis:names:tc:opendocument:xmlns:container", 
    "dc": "http://purl.org/dc/elements/1.1/", 
    "xhtml": "http://www.w3.org/1999/xhtml", 
}


class CachedMeta(type):

    def __init__(self, /, *args, cache_cls=None, **kwargs):
        ns = self.__dict__
        if "__cache_instance__" not in ns:
            if not callable(cache_cls):
                cache_cls = next((
                    b.__dict__["__ceche_cls__"] for b in self.__mro__
                    if callable(b.__dict__.get("__ceche_cls__"))
                ), WeakValueDictionary)
            self.__cache_instance__ = cache_cls()
        if "__cache_state__" not in ns:
            self.__cache_state__ = WeakKeyDictionary()

    def __call__(self, /, key=undefined, *args, **kwargs):
        if key is undefined:
            return super().__call__(**kwargs)
        ns = self.__dict__
        get_key = ns.get("__cache_get_key__")
        if callable(get_key):
            key = get_key(key, *args, **kwargs)
        elif get_key is not None:
            return super().__call__(key, *args, **kwargs)
        check_key = ns.get("__cache_check_key__")
        if callable(check_key) and not check_key(key):
            return super().__call__(key, *args, **kwargs)
        get_state = ns.get("__cache_get_state__")
        set_state = ns.get("__cache_set_state__")
        try:
            val = self.__cache_instance__[key]
        except KeyError:
            val = self.__cache_instance__[key] = super().__call__(key, *args, **kwargs)
            if callable(set_state):
                pass
            elif callable(get_state):
                self.__cache_state__[val] = get_state(key, *args, **kwargs)
        else:
            if callable(set_state):
                set_state(val, key, *args, **kwargs)
            elif callable(get_state):
                state = self.__cache_state__.get(val)
                state_new = self.__cache_state__[val] = get_state(key, *args, **kwargs)
                if state is not state_new and state != state_new:
                    val = self.__cache_instance__[key] = super().__call__(key, *args, **kwargs)
        return val


@MutableMapping.register
class ElementAttribProxy(metaclass=CachedMeta):
    __const_keys__: tuple[str, ...] = ()
    __protected_keys__: tuple[str, ...] = ()
    __cache_check_key__ = lambda obj: isinstance(obj, Element)
    __is_wrap_class__ = True
    __ceche_cls__ = WeakKeyDictionary if USE_BUILTIN_XML else WeakValueDictionary

    def __init__(self, root, /):
        self._root = root
        self._attrib = root.attrib
        if USE_BUILTIN_XML:
            self._nsmap = nsmap = {}
        else:
            self._nsmap = nsmap = root.nsmap
        if self.__const_keys__:
            self.__const_keys__ = frozenset(
                resolve_prefix(key, nsmap, NAMESPACES) for key in type(self).__const_keys__
            )
        if self.__protected_keys__:
            self.__protected_keys__ = frozenset(
                resolve_prefix(key, nsmap, NAMESPACES) for key in type(self).__protected_keys__
            )

    def __init_subclass__(
        cls, 
        /, 
        get_key=None, 
        check_key=None, 
        get_state=None, 
        set_state=None, 
        **kwargs, 
    ):
        if callable(get_key):
            self.__cache_get_key__ = get_key
        if isclass(check_key) and issubclass(check_key, object) or type(check_key) is tuple:
            self.__cache_check_key__ = lambda obj, _t: isinstance(obj, _t)
        elif type(check_key) in (set, frozenset):
            self.__cache_check_key__ = check_key.__contains__
        elif callable(check_key):
            self.__cache_check_key__ = check_key
        if callable(get_state):
            self.__cache_get_state__ = get_state
        if callable(set_state):
            self.__cache_set_state__ = set_state

    def __contains__(self, key, /):
        if not isinstance(key, str) or not key:
            return False
        return resolve_prefix(key, self._nsmap, NAMESPACES) in self._attrib

    def __delitem__(self, key, /):
        if isinstance(key, (int, slice)):
            del self._root[key]
        elif isinstance(key, str):
            if not key:
                raise ValueError("empty key not allowed")
            key = resolve_prefix(key, self._nsmap, NAMESPACES)
            if key in self.__const_keys__ or key in self.__protected_keys__:
                raise LookupError(f"not allowed to delete key: {key}")
            del self._attrib[key]
        else:
            raise TypeError("only accept `key` type: int, slice and str")

    def __eq__(self, other, /):
        if type(self) is not type(other):
            return NotImplemented
        return self._root is other._root

    def __getitem__(self, key, /):
        if isinstance(key, (int, slice)):
            wrap_cls = next(cls for cls in type(self).__mro__ if cls.__dict__.get("__is_wrap_class__"))
            if isinstance(key, int):
                return wrap_cls(self._root[key])
            return list(map(wrap_cls, self._root[key]))
        elif isinstance(key, str):
            if not key:
                raise ValueError("empty key not allowed")
            return self._attrib[resolve_prefix(key, self._nsmap, NAMESPACES)]
        else:
            raise TypeError("only accept `key` type: int, slice and str")

    def __hash__(self, /):
        return hash(self._root)

    def __iter__(self, /):
        return iter(self._attrib)

    def __len__(self, /):
        return len(self._attrib)

    def __setitem__(self, key, val, /):
        if not isinstance(key, str):
            raise TypeError("only accept `key` type: str")
        if not key:
            raise ValueError("empty key not allowed")
        key = resolve_prefix(key, self._nsmap, NAMESPACES)
        if key in self.__const_keys__:
            raise LookupError(f"not allowed to set key: {key!r}")
        self._attrib[key] = val

    def __repr__(self, /):
        return f"<{type(self).__qualname__}({self._attrib!r}) at {hex(id(self))}>"

    @cached_property
    def attrib(self, /):
        return MappingProxyType(self._attrib)

    @property
    def nsmap(self, /):
        return self._nsmap

    @property
    def proxy(self, /):
        return self

    def iter(self, /):
        wrap_cls = next(cls for cls in type(self).__mro__ if cls.__dict__.get("__is_wrap_class__"))
        return map(wrap_cls, self._root.iterfind("*"))

    def list(self, /):
        return list(self.iter())

    def keys(self, /):
        return self._attrib.keys()

    def values(self, /):
        return self._attrib.values()

    def items(self, /):
        return self._attrib.items()

    def clear(self, /):
        const_keys = self.__const_keys__
        protected_keys = self.__protected_keys__
        attrib = self._attrib
        if const_keys or protected_keys:
            for key in tuple(attrib):
                if key in __const_keys__ or key in protected_keys:
                    continue
                del attrib[key]
        else:
            attrib.clear()

    def get(self, key, /, default=None):
        try:
            return self[key]
        except LookupError:
            return default

    def pop(self, key, /, default=undefined):
        try:
            r = self[key]
        except LookupError:
            if default is undefined:
                raise
            return default
        else:
            del self[key]
            return r

    def popitem(self, /):
        const_keys = self.__const_keys__
        protected_keys = self.__protected_keys__
        for key, val in reversed(self._attrib.items()):
            if not (key in const_keys or key in protected_keys):
                del self._attrib[key]
                return (key, val)
        raise LookupError("no items to pop")

    def setdefault(self, key, /, default=""):
        if not isinstance(key, str):
            raise TypeError("only accept `key` type: str")
        try:
            return self[key]
        except LookupError:
            self[key] = default
            return default

    def sort(self, key=id, reverse=False, use_backend_element=False):
        if use_backend_element:
            self._root[:] = sorted(self._root, key=key, reverse=reverse)
        else:
            self._root[:] = (e._root for e in sorted(self.iter(), key=key, reverse=reverse))

    def update(self, /, attrib=None, merge=False):
        el_set(self._root, attrib=attrib, namespaces=NAMESPACES, merge=merge)


class ElementProxy(ElementAttribProxy):
    __is_wrap_class__ = True

    def __repr__(self, /):
        attrib = self._attrib or ""
        text = self.text
        text = f" {text=!r}" if text and text.strip() else ""
        tail = self.tail
        tail = f" {tail=!r}" if tail and tail.strip() else ""
        return f"<{self.tag}>{attrib}{text}{tail}"

    @property
    def length(self, /):
        return len(self._root)

    @property
    def tag(self, /):
        return self._root.tag

    @property
    def text(self, /):
        return self._root.text

    @text.setter
    def text(self, text, /):
        self._root.text = text

    @property
    def tail(self, /):
        return self._root.tail

    @tail.setter
    def tail(self, text, /):
        self._root.tail = text

    def clear(self, /):
        self._root.clear()

    def update(self, /, attrib=None, text=None, tail=None, merge=False):
        el_set(self._root, attrib=attrib, text=text, tail=tail, namespaces=NAMESPACES, merge=merge)

    def add(self, name, /, attrib=None, text=None, tail=None):
        wrap_cls = next(cls for cls in type(self).__mro__ if cls.__dict__.get("__is_wrap_class__"))
        return wrap_cls(el_add(self._root, name=name, attrib=attrib, text=text, tail=tail, namespaces=NAMESPACES))

    def delete(self, path, /):
        el_del(self._root, path, namespaces=NAMESPACES)

    def find(self, path, /):
        return next(self.iterfind(path), None)

    def iterfind(self, path, /):
        return map(
            next(cls for cls in type(self).__mro__ if cls.__dict__.get("__is_wrap_class__")), 
            el_iterfind(self._root, path, NAMESPACES), 
        )

    def set(
        self, 
        path=None, 
        /, 
        name=None, 
        attrib=None, 
        text=None, 
        tail=None, 
        merge=False, 
    ):
        el = el_set(
            self._root, 
            path, 
            name=name, 
            attrib=attrib, 
            text=text, 
            tail=tail, 
            namespaces=NAMESPACES, 
            merge=merge, 
        )
        if el is not None:
            return next(cls for cls in type(self).__mro__ if cls.__dict__.get("__is_wrap_class__"))(el)

    def setfind(
        self, 
        name, 
        /, 
        find_attrib=None, 
        attrib=None, 
        text=None, 
        tail=None, 
        merge=False, 
        delete=False, 
        auto_add=False, 
    ):
        el = el_setfind(
            self._root, 
            name=name, 
            find_attrib=find_attrib, 
            attrib=attrib, 
            text=text, 
            tail=tail, 
            namespaces=NAMESPACES, 
            merge=merge, 
            delete=delete, 
            auto_add=auto_add, 
        )
        if el is not None:
            return next(cls for cls in type(self).__mro__ if cls.__dict__.get("__is_wrap_class__"))(el)

