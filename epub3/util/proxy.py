#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io>"
__all__ = ["NAMESPACES", "PREFIXES", "ElementAttribProxy", "ElementProxy", "auto_property", "proxy_property"]

from collections import UserString
from functools import cached_property, partial
from inspect import isclass, signature
from re import compile as re_compile, escape as re_escape, Pattern
from typing import overload, Callable, Container, Final, ItemsView, Mapping, MutableMapping, Optional
from types import MappingProxyType
from weakref import WeakKeyDictionary, WeakValueDictionary

try:
    from lxml.etree import register_namespace, _Element as Element, _ElementTree as ElementTree # type: ignore
    USE_BUILTIN_XML = False
except ModuleNotFoundError:
    from xml.etree.ElementTree import register_namespace, Element, ElementTree # type: ignore
    USE_BUILTIN_XML = True

from .helper import items
from .stream import PyLinq
from .undefined import undefined
from .xml import el_add, el_del, el_iterfind, el_set, el_setfind, resolve_prefix


NAMESPACES: Final = {
    "containerns": "urn:oasis:names:tc:opendocument:xmlns:container", 
    "daisy": "http://www.daisy.org/z3986/2005/ncx/", 
    "dc": "http://purl.org/dc/elements/1.1/", 
    "ds": "http://www.w3.org/2000/09/xmldsig#", 
    "epub": "http://www.idpf.org/2007/ops", 
    "enc": "http://www.w3.org/2001/04/xmlenc#",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/", 
    "ns": "http://www.idpf.org/2016/encryption#compression", 
    "opf": "http://www.idpf.org/2007/opf", 
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#", 
    "smil": "http://www.w3.org/ns/SMIL", 
    "svg": "http://www.w3.org/2000/svg", 
    "html": "http://www.w3.org/1999/xhtml", 
    "wsdl": "http://schemas.xmlsoap.org/wsdl/", 
    "xhtml": "http://www.w3.org/1999/xhtml", 
    "xml": "http://www.w3.org/XML/1998/namespace", 
    "xs": "http://www.w3.org/2001/XMLSchema", 
    "xsi": "http://www.w3.org/2001/XMLSchema-instance", 
}
# See: https://www.w3.org/TR/epub/#sec-reserved-prefixes
PREFIXES: Final = {
    # Package document reserved prefixes
    "a11y": "http://www.idpf.org/epub/vocab/package/a11y/#", 
    "dcterms": "http://purl.org/dc/terms/", 
    "marc": "http://id.loc.gov/vocabulary/", 
    "media": "http://www.idpf.org/epub/vocab/overlays/#", 
    "onix": "http://www.editeur.org/ONIX/book/codelists/current.html#", 
    "rendition": "http://www.idpf.org/vocab/rendition/#", 
    "schema": "http://schema.org/", 
    "xsd": "http://www.w3.org/2001/XMLSchema#", 
    # Other reserved prefixes
    "msv": "http://www.idpf.org/epub/vocab/structure/magazine/#", 
    "prism": "http://www.prismstandard.org/specifications/3.0/PRISM_CV_Spec_3.0.htm#", 
}

for prefix, uri in NAMESPACES.items():
    register_namespace(prefix, uri)


class CachedMeta(type):

    def __init__(self, /, *args, cache_cls=None, **kwargs):
        ns = self.__dict__
        if "__cache_instance__" not in ns:
            if not callable(cache_cls):
                cache_cls = next((
                    b.__dict__["__cache_cls__"] for b in self.__mro__
                    if callable(b.__dict__.get("__cache_cls__"))
                ), WeakValueDictionary)
            self.__cache_instance__ = cache_cls()
        if "__cache_state__" not in ns:
            self.__cache_state__ = WeakKeyDictionary()
        if "__init__" in ns:
            self.__signature__ = signature(ns["__init__"])

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


class AttrInfoProxy(MutableMapping):
    __slots__ = ("__backend__",)

    def __init__(self, backend, /):
        super().__setattr__("__backend__", backend)

    def __contains__(self, key, /):
        return key in self.__backend__

    def __delitem__(self, key, /):
        del self.__backend__[key]
        return self

    def __getattr__(self, attr):
        return getattr(self.__backend__, attr)

    def __getitem__(self, key, /):
        return self.__backend__[key]

    def __iter__(self, /):
        return iter(self.__backend__)

    def __len__(self, /):
        return len(self.__backend__)

    def __setattr__(self, attr, value, /):
        raise TypeError("can't set any attributes")

    def __setitem__(self, key, value, /):
        self.__backend__[key] = value
        return self

    def __repr__(self, /):
        return repr(self.__backend__._attrib)

    def keys(self, /):
        return self.__backend__.keys()

    def values(self, /):
        return self.__backend__.values()

    def items(self, /):
        return self.__backend__.items()

    def clear(self, /):
        self.__backend__.clear()
        return self

    def get(self, key, /, default=undefined):
        if default is undefined:
            return self.__backend__.get(key)
        return self.__backend__.get(key, default)

    def pop(self, key, /, default=undefined):
        if default is undefined:
            return self.__backend__.pop(key)
        return self.__backend__.pop(key, default)

    def popitem(self, /):
        return self.__backend__.popitem()

    def setdefault(self, key, /, default=undefined):
        if default is undefined:
            return self.__backend__.setdefault(key)
        return self.__backend__.setdefault(key, default)

    def merge(self, attrib=None, /, **attrs):
        self.__backend__.merge(attrib, **attrs)
        return self

    def update(self, attrib=None, /, **attrs):
        self.__backend__.update(attrib, **attrs)
        return self


class ElementInfoProxy(MutableMapping):
    __slots__ = ("__backend__",)

    def __init__(self, backend, /):
        super().__setattr__("__backend__", backend)

    def __repr__(self, /):
        return "{%s}" % ", ".join("%r: %r" %t for t in zip(("tag", "attrib", "text", "tail"), self))

    def __contains__(self, key, /):
        return key in ("tag", "attrib", "text", "tail")

    def __iter__(self, /):
        backend = self.__backend__
        return (getattr(backend, key) for key in ("tag", "attrib", "text", "tail"))

    def __len__(self, /):
        return 4

    def __delitem__(self, key, /):
        if key in ("text", "tail"):
            setattr(self.__backend__, key, None)
        elif key in ("tag", "attrib"):
            raise TypeError(f"can't set key: {key!r}")
        else:
            raise KeyError(key)

    def __getitem__(self, key, /):
        if key in ("tag", "attrib", "text", "tail"):
            return getattr(self.__backend__, key)
        raise KeyError(key)

    def __setitem__(self, key, value, /):
        if key in ("text", "tail"):
            setattr(self.__backend__, key, value)
        else:
            raise TypeError(f"can't set key: {key!r}")

    __delattr__ = __delitem__
    __getattr__ = __getitem__
    __setattr__ = __setitem__


def strip_key(key: str) -> str:
    key = key[key.rfind("}")+1:]
    key = key[key.rfind(":")+1:]
    return key.replace("-", "_")


class OperationalString(UserString):

    def __add__(self, value, /):
        if value is None:
            return self.data
        return self.data + str(value)

    def __radd__(self, value, /):
        if value is None:
            return self.data
        return str(value) + self.data

    def __iadd__(self, value, /):
        if value is not None:
            self.data += str(value)
        return self

    __or__ = __add__
    __ror__ = __radd__
    __ior__ = __iadd__

    def __matmul__(self, value, /):
        self.data = value
        return self

    def __mul__(self, n, /):
        return self.data * n

    __rmul__ = __mul__

    def __imul__(self, n, /):
        self.data *= n
        return self

    __xor__ = __radd__
    __rxor__ = __add__

    def __ixor__(self, value, /):
        if value is None:
            return self.data
        self.data = str(value) + self.data
        return self

    def __lshift__(self, value, /):
        if value is None:
            return self.data
        return self.data.removeprefix(str(value))

    def __ilshift__(self, value, /):
        if value is not None:
            self.data = self.data.removeprefix(str(value))
        return self

    def __rshift__(self, value, /):
        if value is None:
            return self.data
        return self.data.removesuffix(str(value))

    def __irshift__(self, value, /):
        if value is not None:
            self.data = self.data.removesuffix(str(value))
        return self

    def __sub__(self, value, /):
        if value is None:
            return self.data
        return self.data.replace(str(value), "")

    def __isub__(self, value, /):
        if value is not None:
            self.data = self.data.replace(str(value), "")
        return self

    def __neg__(self, /):
        self.data = self.data.lstrip()
        return self

    def __pos__(self, /):
        self.data = self.data.rstrip()
        return self

    def __invert__(self, /):
        self.data = self.data.strip()
        return self

    def __truediv__(self, value, /):
        if value is None:
            return self.data
        return re_compile("^(?:%s)*" % re_escape(str(value))).sub("", self.data)

    def __itruediv__(self, value, /):
        if value is not None and (data := self.data):
            self.data = re_compile("^(?:%s)*" % re_escape(str(value))).sub("", self.data)
        return self

    def __floordiv__(self, value, /):
        if value is None:
            return self.data
        return re_compile("(?:%s)*$" % re_escape(str(value))).sub("", self.data)

    def __ifloordiv__(self, value, /):
        if value is not None and (data := self.data):
            self.data = re_compile("(?:%s)*$" % re_escape(str(value))).sub("", data)
        return self

    def __mod__(self, value, /):
        data = self.data
        if value is None:
            return data
        s = "(?:%s)*" % re_escape(str(value))
        data = re_compile("^"+s).sub("", data)
        return re_compile(s+"$").sub("", data)

    def __imod__(self, value, /):
        if value is not None and (data := self.data):
            s = "(?:%s)*" % re_escape(str(value))
            data = re_compile("^"+s).sub("", data)
            self.data = re_compile(s+"$").sub("", data)
        return self


def auto_property(
    key: Optional[str] = None, 
    setable: bool = False, 
    delable: bool = False, 
) -> property:
    class AttribProxy(OperationalString, str): # type: ignore
        __slots__ = ()
        @staticmethod
        def __init__(*args, **kwargs):
            pass
        @staticmethod
        def __init_subclass__(**kwargs):
            raise TypeError("subclassing is not allowed")
        @staticmethod
        def __getattr__(_, /): # type: ignore
            if key is None:
                return instance.tail or ""
            elif key == "":
                return instance.text or ""
            else:
                return instance.get(key, "")
        @staticmethod
        def __delattr__(): # type: ignore
            try:
                deleter(instance)
            except UnboundLocalError:
                raise TypeError("can't delete attribute")
        @staticmethod
        def __setattr__(_, value, /): # type: ignore
            try:
                setter(instance, value)
            except UnboundLocalError:
                raise TypeError("can't set attribute")
    if key:
        key = resolve_prefix(key, NAMESPACES)
    proxy = AttribProxy()
    instance = None
    def getter(self, /):
        nonlocal instance
        instance = self
        return proxy
    auto_property = property(getter)
    if setable:
        def setter(self, value, /):
            if key is None:
                self.tail = value
            elif key == "":
                self.text = value
            else:
                self[key] = value
        auto_property = auto_property.setter(setter)
    if delable:
        def deleter(self, /):
            if key is None:
                self.tail = None
            elif key == "":
                self.text = None
            else:
                self.pop(key, None)
        auto_property = auto_property.deleter(deleter)
    return auto_property


@overload
def proxy_property(fget: None, /, key: Optional[str] = "") -> Callable[[Callable], property]: ...
@overload
def proxy_property(fget: Callable, /, key: Optional[str] = "") -> property: ...
def proxy_property(fget=None, /, key = ""):
    if fget is None:
        return partial(proxy_property, key=key)
    class AttribProxy(OperationalString, str):  # type: ignore
        __slots__ = ()
        @staticmethod
        def __init__(*args, **kwargs):
            pass
        @staticmethod
        def __init_subclass__(**kwargs):
            raise TypeError("subclassing is not allowed")
        @staticmethod
        def __getattr__(_, /): # type: ignore
            if key is None:
                return instance.tail or ""
            elif key == "":
                return instance.text or ""
            else:
                return instance.get(key, "")
        @staticmethod
        def __delattr__(): # type: ignore
            deleter()
        @staticmethod
        def __setattr__(_, value, /): # type: ignore
            setter(value)
    if key:
        key = resolve_prefix(key, NAMESPACES)
    proxy = AttribProxy()
    instance = None
    def getter(self, /):
        nonlocal instance
        instance = fget(self)
        return proxy
    def setter(value, /):
        if key is None:
            instance.tail = value
        elif key == "":
            instance.text = value
        else:
            instance[key] = value
    def deleter():
        if key is None:
            instance.tail = None
        elif key == "":
            instance.text = None
        else:
            instance.pop(key, None)
    return property(getter)


@MutableMapping.register
class ElementAttribProxy(metaclass=CachedMeta):
    __const_keys__: tuple[str, ...] = ()
    __protected_keys__: tuple[str, ...] = ()
    __cache_check_key__ = lambda obj: isinstance(obj, Element)
    __cache_cls__ = WeakKeyDictionary if USE_BUILTIN_XML else WeakValueDictionary
    __wrap_class__: "type[ElementAttribProxy]"

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
        namespaces = cls.__dict__
        const_keys = namespaces.get("__const_keys__")
        if const_keys:
            for key in const_keys:
                stripped_key = strip_key(key)
                if stripped_key not in namespaces:
                    setattr(cls, stripped_key, auto_property(key))
        protected_keys = namespaces.get("__protected_keys__")
        if protected_keys:
            for key in protected_keys:
                stripped_key = strip_key(key)
                if stripped_key not in namespaces:
                    setattr(cls, stripped_key, auto_property(key, setable=True))
        optional_keys = namespaces.get("__optional_keys__")
        if optional_keys:
            for key in optional_keys:
                stripped_key = strip_key(key)
                if stripped_key not in namespaces:
                    setattr(cls, stripped_key, auto_property(key, setable=True, delable=True))
        if "__wrap_class__" not in namespaces:
            for base_cls in cls.__mro__:
                if "__wrap_class__" in base_cls.__dict__:
                    cls.__wrap_class__ = base_cls.__wrap_class__
                    break
                elif cls.__dict__.get("__is_wrap_class__"):
                    cls.__wrap_class__ = base_cls
                    break

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
            if key in self.__const_keys__ or key in self.__protected_keys__:
                raise LookupError(f"not allowed to delete key: {key}")
            del self._attrib[key]
        else:
            raise TypeError("only accept `key` type: int, slice and str")
        return self

    def __eq__(self, other, /):
        if type(self) is not type(other):
            return NotImplemented
        return self._root is other._root

    def __getitem__(self, key, /):
        if isinstance(key, str):
            if not key:
                raise ValueError("empty key not allowed")
            return self._attrib[resolve_prefix(key, self._nsmap, NAMESPACES)]
        elif isinstance(key, (int, slice)):
            if isinstance(key, int):
                return type(self).wrap(self._root[key])
            return list(map(type(self).wrap, self._root[key]))
        else:
            raise TypeError("only accept `key` type: int, slice and str")

    def __hash__(self, /):
        return hash(self._root)

    @PyLinq.streamify
    def __iter__(self, /):
        return iter(self._attrib)

    def __len__(self, /):
        return len(self._attrib)

    def __setitem__(self, key, value, /):
        if not isinstance(key, str):
            raise TypeError("only accept `key` type: `str`")
        if not key:
            raise ValueError("empty key not allowed")
        if value is None:
            self.pop(key, None)
        else:
            if key in self.__const_keys__:
                raise LookupError(f"not allowed to set key: {key!r}")
            self._attrib[key] = str(value)
        return self

    def __repr__(self, /):
        attrib = self._attrib
        attrib = f", {attrib=!r}" if attrib else ""
        return f"<{type(self).__qualname__}(<{self._root.tag}>{attrib}) at {hex(id(self))}>"

    @classmethod
    def wrap(cls, root, /):
        wrap_class_map = cls.__dict__.get("__wrap_class_map__")
        if not wrap_class_map:
            return cls.__wrap_class__(root)
        for pred, wrap_class in wrap_class_map.items():
            if isinstance(pred, str):
                if pred.startswith("{*}"):
                    if pred[3:] == root.tag or root.tag.endswith(pred[2:]):
                        return wrap_class(root)
                elif pred.startswith("{}"):
                    if pred[2:] == root.tag:
                        return wrap_class(root)
                elif pred.endswith(":*"):
                    if root.tag.startswith(pred[:-1]) or root.tag.startswith(resolve_prefix(pred[:-1], NAMESPACES)):
                        return wrap_class(root)
                elif root.tag == pred or root.tag == resolve_prefix(pred, NAMESPACES):
                    return wrap_class(root)
            elif isinstance(pred, Pattern):
                if pred.search(root.tag) is not None:
                    return wrap_class(root)
            elif isinstance(pred, Container):
                if root.tag in pred:
                    return wrap_class(root)
            elif callable(pred):
                if pred(root):
                    return wrap_class(root)
        return cls.__wrap_class__(root)

    def getproxy(self, key, /):
        if not key:
            return
        key = resolve_prefix(key, self._nsmap, NAMESPACES)
        namespaces = type(self).__dict__
        const_keys = namespaces.get("__const_keys__")
        protected_keys = namespaces.get("__protected_keys__")
        setable = not (const_keys and key in const_keys)
        delable = setable and not (protected_keys and key in protected_keys)
        return auto_property(key, setable=setable, delable=delable).fget(self)

    @cached_property
    def attrib(self, /):
        return AttrInfoProxy(self)

    @property
    def nsmap(self, /):
        return self._nsmap

    @cached_property
    def info(self, /):
        return MappingProxyType({"attrib": self.attrib})

    @property
    def proxy(self, /):
        return self

    @PyLinq.streamify
    def iter(self, /):
        return map(type(self).wrap, self._root.iterfind("*"))

    def list(self, /, mapfn=None):
        if mapfn is None:
            return list(self.iter())
        return list(map(mapfn, self.iter()))

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
                if key in const_keys or key in protected_keys:
                    continue
                del attrib[key]
        else:
            attrib.clear()
        return self

    def get(self, key, /, default=None):
        try:
            return self._attrib[key]
        except LookupError:
            return default

    def pop(self, key, /, default=undefined):
        if key in self.__const_keys__ or key in self.__protected_keys__:
            raise LookupError(f"not allowed to delete key: {key}") 
        try:
            r = self._attrib[key]
        except LookupError:
            if default is undefined:
                raise
            return default
        else:
            del self._attrib[key]
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
            return seself._attriblf[key]
        except LookupError:
            self._attrib[key] = default
            return default

    def sort(self, key=id, reverse=False, use_backend_element=False):
        if use_backend_element:
            self._root[:] = sorted(self._root, key=key, reverse=reverse)
        else:
            self._root[:] = (e._root for e in sorted(self.iter(), key=key, reverse=reverse))
        return self

    def merge(self, attrib=None, /, **attrs):
        if attrib:
            if attrs:
                attrib = dict(attrib, **attrs)
        else:
            attrib = attrs
        if attrib:
            el_set(self._root, attrib=attrib, namespaces=NAMESPACES, merge=True)
        return self

    def update(self, attrib=None, /, **attrs):
        const_keys = self.__const_keys__
        if attrib:
            if attrs:
                attrib = dict(attrib, **attrs)
            elif const_keys and (not isinstance(attrib, Mapping) or any(key in attrib for key in const_keys)):
                attrib = dict(attrib)
            else:
                const_keys = ()
        else:
            attrib = attrs
        if const_keys:
            for key in const_keys:
                attrib.pop(key, None)
        if attrib:
            el_set(self._root, attrib=attrib, namespaces=NAMESPACES, merge=False)
        return self

ElementAttribProxy.__wrap_class__ = ElementAttribProxy


class ElementProxy(ElementAttribProxy):
    __is_wrap_class__ = True

    def __repr__(self, /):
        attrib = self._attrib
        attrib = f", {attrib=!r}" if attrib else ""
        text = self.text
        text = f", {text=!r}" if text and text.strip() else ""
        tail = self.tail
        tail = f", {tail=!r}" if tail and tail.strip() else ""
        return f"<{type(self).__qualname__}(<{self._root.tag}>{attrib}{text}{tail}) at {hex(id(self))}>"

    def getproxy(self, key="", /):
        if not key:
            return auto_property(key, setable=True, delable=True).fget(self)
        return super().getproxy(key)

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
        self._root.text = None if text is None else str(text)

    @property
    def tail(self, /):
        return self._root.tail

    @tail.setter
    def tail(self, text, /):
        self._root.tail = None if text is None else str(text)

    @cached_property
    def info(self, /):
        return ElementInfoProxy(self)

    def clear(self, /):
        self._root.clear()
        return self

    def merge(self, attrib=None, /, text=None, tail=None, **attrs):
        super().merge(attrib, **attrs)
        el_set(self._root, text=text, tail=tail, namespaces=NAMESPACES, merge=True)
        return self

    def update(self, attrib=None, /, text=None, tail=None, **attrs):
        super().update(attrib, **attrs)
        el_set(self._root, text=text, tail=tail, namespaces=NAMESPACES, merge=False)
        return self

    def add(self, name, /, attrib=None, text=None, tail=None):
        return type(self).wrap(el_add(self._root, name=name, attrib=attrib, text=text, tail=tail, namespaces=NAMESPACES))

    def delete(self, path, /):
        if isinstance(path, ElementAttribProxy):
            try:
                self._root.remove(path._root)
            except:
                pass
        else:
            el_del(self._root, path, namespaces=NAMESPACES)
        return self

    def find(self, path, /):
        return next(self.iterfind(path), None)

    @PyLinq.streamify
    def iterfind(self, path, /):
        return map(type(self).wrap, el_iterfind(self._root, path, NAMESPACES))

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
            return type(self).wrap(el)

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
            return type(self).wrap(el)

