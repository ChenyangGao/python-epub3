#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io>"
__version__ = (0, 0, 1)
__all__ = ["ePub", "Metadata", "DCTerm", "Meta", "Link", "Manifest", "Item", "Spine", "Itemref"]

import errno
import io
import os
import os.path as ospath
import posixpath

from copy import deepcopy
from datetime import datetime
from fnmatch import translate as wildcard_translate
from functools import cached_property, partial
from inspect import getfullargspec, isclass
from io import IOBase, TextIOWrapper
from operator import methodcaller
from os import fsdecode, remove, stat, stat_result, PathLike
from pathlib import PurePosixPath
from posixpath import join as joinpath, normpath
from pprint import pformat
from re import compile as re_compile, escape as re_escape, Pattern
from shutil import copy, copyfileobj
from typing import cast, Any, Callable, Container, Mapping, MutableMapping, Optional
from types import MappingProxyType
from uuid import uuid4
from warnings import warn
from weakref import WeakKeyDictionary, WeakValueDictionary
from urllib.parse import quote, unquote
from zipfile import ZipFile, ZIP_STORED

from .util.file import File, RootFS, TemporaryFS, OPEN_MODES
from .util.helper import guess_media_type, values, items
from .util.proxy import proxy_property, ElementAttribProxy, ElementProxy, NAMESPACES
from .util.remap import remap_links
from .util.stream import PyLinq
from .util.xml import el_add, el_del, el_iterfind, el_set
from .util.undefined import undefined, UndefinedType

try:
    from lxml.etree import fromstring, tostring, _Element as Element, _ElementTree as ElementTree # type: ignore
except ModuleNotFoundError:
    from xml.etree.ElementTree import fromstring, tostring, Element, ElementTree # type: ignore


class DCTerm(ElementProxy):
    pass


class Meta(ElementProxy):
    __protected_keys__ = ("property",)
    __optional_keys__ = ("dir", "id", "refines", "scheme", "xml:lang")


class Link(ElementAttribProxy):
    __protected_keys__ = ("href", "rel")
    __optional_keys__ = ("hreflang", "id", "media-type", "properties", "refines")


class Item(ElementAttribProxy):
    __const_keys__ = ("id",)
    __protected_keys__ = ("href", "media-type")
    __optional_keys__ = ("fallback", "media-overlay", "properties")
    __cache_get_state__ = lambda _, manifest: manifest

    def __init__(self, root: Element, manifest, /):
        super().__init__(root)
        self._manifest = manifest

    def __eq__(self, other, /):
        if type(self) is not type(other):
            return NotImplemented
        return self._manifest is other._manifest and self._attrib["href"] == other._attrib["href"]

    def __fspath__(self, /):
        return unquote(self._attrib["href"])

    def __hash__(self, /):
        return hash((self._root, id(self._manifest)))

    def __setitem__(self, key, value, /):
        if key == "href":
            if value is None:
                raise ValueError("can't set href to None")
            self.rename(val)
        else:
            super().__setitem__(key, value)
        return self

    @property
    def filename(self, /):
        return PurePosixPath(joinpath(self.home, self))

    @property
    def home(self, /):
        return PurePosixPath(self._manifest._epub._opf_dir)

    @property
    def name(self, /):
        return self.path.name

    @property
    def path(self, /):
        return PurePosixPath(self)

    @property
    def _parent(self, /):
        return posixpath.dirname(unquote(self._attrib["href"]))

    @property
    def parent(self, /):
        return self.path.parent

    @property
    def parents(self, /):
        return self.path.parents

    @property
    def parts(self, /):
        return self.path.parts

    @property
    def stem(self, /):
        return self.path.stem

    @property
    def suffix(self, /):
        return self.path.suffix

    @property
    def suffixes(self, /):
        return self.path.suffixes

    def update(self, attrib=None, /, **attrs):
        if attrib:
            attrib = dict(attrib)
            if attrs:
                attrib.update(attrs)
        else:
            attrib = attrs
        href = attrib.pop("href", None)
        if href:
            self.rename(href)
        if attrib:
            super().update(attrib)
        return self

    def is_relative_to(self, /, *other):
        return self.path.is_relative_to(*other)

    def joinpath(self, /, *others):
        return PurePosixPath(normpath(joinpath(self._parent, *others)))

    __truediv__ = joinpath

    def relpath(self, other, /):
        return PurePosixPath(posixpath.relpath(other, self._parent))

    def relative_to(self, /, *other):
        return self.path.relative_to(*other)

    def with_name(self, /, name):
        return self.path.with_name(str(name))

    def with_stem(self, /, stem):
        return self.path.with_stem(str(stem))

    def with_suffix(self, /, suffix):
        return self.path.with_suffix(str(suffix))

    def exists(self, /):
        return self._manifest.exists(self)

    def is_file(self, /):
        return self.exists()

    def is_dir(self, /):
        return False

    def is_symlink(self, /):
        return False

    def glob(self, /, pattern="*", ignore_case=False):
        return self._manifest.glob(pattern, self, ignore_case=ignore_case)

    def rglob(self, /, pattern="", ignore_case=False):
        return self._manifest.rglob(pattern, self, ignore_case=ignore_case)

    def iterdir(self, /):
        return self._manifest.iterdir(self)

    def match(self, /, path_pattern, ignore_case=False):
        path_pattern = path_pattern.strip("/")
        if not path_pattern:
            return False
        pattern = joinpath(*posix_glob_translate_iter(path_pattern))
        if ignore_case:
            pattern = "(?i:%s)" % pattern
        return re_compile(pattern).fullmatch(self._attrib["href"]) is not None

    def open(
        self, 
        /, 
        mode="r", 
        buffering=-1, 
        encoding=None, 
        errors=None, 
        newline=None, 
    ):
        return self._manifest.open(
            self,  
            mode=mode, 
            buffering=buffering, 
            encoding=encoding, 
            errors=errors, 
            newline=newline, 
        )

    def read(self, /, buffering=0):
        return self._manifest.read(self, buffering=buffering)

    read_bytes = read

    def read_text(self, /, encoding=None):
        return self._manifest.read_text(self, encoding=encoding)

    def remove(self, /):
        self._manifest.remove(self)
        return self

    def rename(self, dest_href, /, repair=False):
        return self._manifest.rename(self, dest_href, repair=repair)

    def batch_rename(self, mapper, /, predicate=None, repair=False):
        return self._manifest.batch_rename(self, mapper, predicate=predicate, repair=repair)

    def replace(self, href, /):
        self._manifest.replace(self, href)
        return self

    def stat(self, /) -> Optional[stat_result]:
        return self._manifest.stat(self)

    def touch(self, /):
        self._manifest.touch(self)
        return self

    unlink = remove

    def write(self, /, data):
        return self._manifest.write(self, data)

    write_bytes = write

    def write_text(self, /, text, encoding=None, errors=None, newline=None):
        return self._manifest.write_text(self, text, encoding=encoding, errors=errors, newline=newline)


class Itemref(ElementAttribProxy):
    __const_keys__ = ("idref",)
    __optional_keys__ = ("id", "linear", "properties")

    @property
    def linear(self, /):
        return "no" if self._attrib.get("linear") == "no" else "yes"

    @linear.setter
    def linear(self, value, /):
        self._attrib["linear"] = "no" if value == "no" else "yes"


class Metadata(ElementProxy):
    __wrap_class_map__ = {"{*}meta": Meta, "{*}": Link, "dc:*": DCTerm}

    def __repr__(self, /):
        return f"{super().__repr__()}\n{pformat(self.iter().list())}"

    @property
    def info(self, /):
        return tuple(meta.info for meta in self.iter())

    def add(
        self, 
        name: str = "meta", 
        /, 
        attrib: Optional[Mapping] = None, 
        text: Optional[str] = None, 
        tail: Any = undefined, 
        **_disregards, 
    ):
        return super().add(name, attrib=attrib, text=text)

    def dc(
        self, 
        name: str, 
        text_value: UndefinedType | Optional[str] = undefined, 
        /, 
        find_attrib: Optional[Mapping] = None, 
        attrib: Optional[Mapping] = None, 
        text: Optional[str] = None, 
        merge: bool = False, 
        delete: bool = False, 
        auto_add: bool = False, 
    ):
        if text_value is not undefined:
            if find_attrib:
                find_attrib = {**find_attrib, "": text_value}
            else:
                find_attrib = {"": text_value}
        return self.setfind(
            "dc:%s" % name, 
            find_attrib=find_attrib, 
            attrib=attrib, 
            text=text, 
            merge=merge, 
            delete=delete, 
            auto_add=auto_add, 
        )

    def meta(
        self, 
        preds: str = "", 
        /, 
        find_attrib: Optional[Mapping] = None, 
        attrib: Optional[Mapping] = None, 
        text: Optional[str] = None, 
        merge: bool = False, 
        delete: bool = False, 
        auto_add: bool = False, 
    ):
        return self.setfind(
            "{*}meta%s" % preds, 
            find_attrib=find_attrib, 
            attrib=attrib, 
            text=text, 
            merge=merge, 
            delete=delete, 
            auto_add=auto_add, 
        )

    def name_meta(
        self, 
        name, 
        content: Optional[str] = None, 
        /, 
        find_attrib: Optional[Mapping] = None, 
        attrib: Optional[Mapping] = None, 
        text: Optional[str] = None, 
        merge: bool = False, 
        delete: bool = False, 
        auto_add: bool = False, 
    ):
        if find_attrib:
            find_attrib = {**find_attrib, "name": name}
        else:
            find_attrib = {"name": name}
        if content is not None:
            find_attrib["content"] = content
        return self.meta(
            find_attrib=find_attrib, 
            attrib=attrib, 
            text=text, 
            merge=merge, 
            delete=delete, 
            auto_add=auto_add, 
        )

    def property_meta(
        self, 
        property, 
        text_value: UndefinedType | Optional[str] = undefined, 
        /, 
        find_attrib: Optional[Mapping] = None, 
        attrib: Optional[Mapping] = None, 
        text: Optional[str] = None, 
        merge: bool = False, 
        delete: bool = False, 
        auto_add: bool = False, 
    ):
        if find_attrib:
            find_attrib = {**find_attrib, "property": property}
        else:
            find_attrib = {"property": property}
        if text_value is not undefined:
            find_attrib[""] = text_value
        return self.meta(
            find_attrib=find_attrib, 
            attrib=attrib, 
            text=text, 
            merge=merge, 
            delete=delete, 
            auto_add=auto_add, 
        )


class ManifestProxy(ElementAttribProxy):
    __optional_keys__ = ("id",)


class Manifest(dict[str, Item]):

    def __init__(self, /, root: Element, epub):
        self._root = root
        self._attrib = root.attrib
        self._epub = epub
        self._proxy = ManifestProxy(root)
        self._href_to_id: dict[str, str] = {}
        self._href_to_file: dict[str, File] = {}
        if len(root):
            href_to_id = self._href_to_id
            dangling_items = []
            for item in root.iterfind("{*}item"):
                id = item.attrib.get("id")
                href = item.attrib.get("href")
                if id is None or not href:
                    dangling_items.append(item)
                    continue
                id = cast(str, id)
                href = cast(str, unquote(href))
                super().__setitem__(id, Item(item, self))
                href_to_id[href] = id
            if dangling_items:
                for item in reversed(dangling_items):
                    root.remove(item)
                    warn(f"removed a dangling item element: {item!r}")
            zfile = epub.__dict__.get("_zfile")
            opf_dir = epub._opf_dir
            if zfile:
                href_to_file = self._href_to_file
                for href in href_to_id:
                    zpath = joinpath(opf_dir, href)
                    zinfo = zfile.NameToInfo.get(zpath)
                    if not zinfo or zinfo.is_dir():
                        warn(f"missing file in original epub: {href!r}")
                        href_to_file[href] = File(str(uuid4()), self._workfs)
                    else:
                        href_to_file[href] = File(zpath, zfile, open_modes="r")

    def __init_subclass__(self, /, **kwargs):
        raise TypeError("subclassing is not allowed")

    def __call__(self, href, /):
        if isinstance(href, Item):
            if href not in self:
                raise LookupError(f"no such item: {href!r}")
            return href
        if isinstance(href, (bytes, PathLike)):
            href = fsdecode(href)
        else:
            href = str(href)
        assert (href := href.strip("/")), "empty href"
        try:
            id = self._href_to_id[href]
        except LookupError as e:
            raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}") from e
        return super().__getitem__(id)

    def __contains__(self, other, /):
        if isinstance(other, Item):
            return other._manifest is self and super().__contains__(other["id"])
        return super().__contains__(other)

    def __delitem__(self, key, /):
        pop = self.pop
        if isinstance(key, int):
            el = self._root[key]
            try:
                id = el.attrib["id"]
            except AttributeError:
                try:
                    self._root.remove(el)
                except:
                    pass
            else:
                pop(id)
        elif isinstance(key, slice):
            root = self._root
            for el in root[key]:
                try:
                    id = el.attrib["id"]
                except AttributeError:
                    try:
                        root.remove(el)
                    except:
                        pass
                else:
                    pop(id, None)
        elif isinstance(key, Item):
            if key not in self:
                raise LookupError(f"no such item: {key!r}")
            pop(key["id"])
        elif isinstance(key, str):
            pop(key)
        else:
            raise TypeError("`key` only accepts: `str`, `int`, `slice`, `Item`")
        return self

    def __getitem__(self, key, /):
        def wrap(el):
            try:
                if el.tag == "item" or el.tag.endswith("}item"):
                    return Item(el, self)
                return ElementProxy(el)
            except AttributeError:
                return el
        if isinstance(key, int):
            return wrap(self._root[key])
        elif isinstance(key, slice):
            return list(map(wrap, self._root[key]))
        elif isinstance(key, Item):
            if key not in self:
                raise LookupError(f"no such item: {key!r}")
            return key
        elif isinstance(key, str):
            return super().__getitem__(key)
        else:
            raise TypeError("`key` only accepts: `str`, `int`, `slice`, `Item`")

    def __setitem__(self, id, value, /):
        if id not in self:
            raise LookupError(f"no such item: {id!r}")
        if isinstance(id, Item):
            item = id
        else:
            item = super().__getitem__(id)
        href = unquote(item._attrib["href"])
        if isinstance(value, str):
            self.rename(href, value)
        elif isinstance(value, bytes):
            self.write(href, value)
        elif isinstance(value, Mapping):
            if "open" in value and callable(value["open"]):
                self._href_to_file[href] = File(value, open_modes="rb")
            else:
                item.update(value)
        else:
            self._href_to_file[href] = File(value, open_modes="rb")
        return self

    @cached_property
    def _workfs(self, /):
        if self._epub._maketemp:
            return TemporaryFS(self._epub._workroot)
        else:
            return RootFS(self._epub._workroot)

    @cached_property
    def href_to_id(self, /):
        return MappingProxyType(self._href_to_id)

    @cached_property
    def href_to_file(self, /):
        return MappingProxyType(self._href_to_file)

    @property
    def home(self, /):
        return self._epub._opf_dir

    @property
    def attrib(self, /):
        return self._attrib

    @property
    def proxy(self, /):
        return self._proxy

    @property
    def info(self, /):
        return tuple(item.info for item in self.values())

    delete = __delitem__

    def clear(self, /):
        self._root.clear()
        self._href_to_file.clear()
        self._href_to_id.clear()
        super().clear()
        return self

    def pop(self, id, /, default=undefined):
        if id not in self:
            if default is undefined:
                raise LookupError(f"no such item: {id!r}")
            return default
        if isinstance(id, Item):
            id = id["id"]
        item = super().pop(id)
        try:
            self._root.remove(item._root)
        except:
            pass
        href = unquote(item._attrib["href"])
        self._href_to_id.pop(href, None)
        file = self._href_to_file.pop(href, None)
        if file is not None and file.check_open_mode("w"):
            try:
                file.remove()
            except:
                pass
        return item

    def popitem(self, /):
        id, item = super().popitem()
        try:
            self._root.remove(item._root)
        except:
            pass
        href = unquote(item._attrib["href"])
        self._href_to_id.pop(href, None)
        file = self._href_to_file.pop(href, None)
        if file is not None and file.check_open_mode("w"):
            try:
                file.remove()
            except:
                pass
        return id, item

    def set(self, id, value, /):
        if isinstance(id, Item):
            if id not in self:
                raise LookupError(f"no such item: {id!r}")
            item = id
        else:
            item = super().get(id)
        if item is None:
            if isinstance(value, str):
                item = self.add(href, id=id)
            elif isinstance(value, Mapping) and "href" in value:
                if "open" in value and callable(value["open"]):
                    item = self.add(value["href"], value, id=id)
                else:
                    item = self.add(value["href"], id=id, attrib=value)
            else:
                raise LookupError(f"no such item: {id!r}")
        else:
            href = unquote(item._attrib["href"])
            if isinstance(value, str):
                self.rename(href, value)
            elif isinstance(value, bytes):
                self.write(href, value)
            elif isinstance(value, Mapping):
                if "open" in value and callable(value["open"]):
                    self._href_to_file[href] = File(value, open_modes="rb")
                else:
                    item.update(value)
            else:
                self._href_to_file[href] = File(value, open_modes="rb")
        return item

    def setdefault(self, id, value, /):
        if isinstance(id, Item):
            if id not in self:
                raise LookupError(f"no such item: {id!r}")
            item = id
        else:
            item = super().get(id)
        if item is None:
            if isinstance(value, str):
                item = self.add(value, id=id)
            elif isinstance(value, Mapping) and "href" in value:
                if "open" in value and callable(value["open"]):
                    item = self.add(value["href"], value, id=id)
                else:
                    item = self.add(value["href"], id=id, attrib=value)
            else:
                raise LookupError(f"no such item: {id!r}")
        else:
            if isinstance(value, Mapping) and not ("open" in value and callable(value["open"])):
                item.merge(value)
        return item

    def merge(self, id_or_attrib=None, /, **attrs):
        if attrs:
            if isinstance(id_or_attrib, Item):
                item = id_or_attrib
                if item not in self:
                    raise LookupError(f"no such item: {item!r}")
                item.merge(attrib=attrs)
            elif isinstance(id_or_attrib, str):
                id = id_or_attrib
                item = super().get(id)
                if item is None:
                    if "href" in attrs:
                        href = attrs.pop("href")
                        self.add(href, id=id, attrib=attrs)
                    else:
                        raise LookupError(f"no such item: {id!r}")
                else:
                    item.merge(attrs)
            else:
                self._proxy.merge(id_or_attrib, **attrs)
        elif isinstance(id_or_attrib, Mapping):
            self._proxy.merge(id_or_attrib)
        return self

    def update(self, id_or_attrib=None, /, **attrs):
        if attrs:
            if isinstance(id_or_attrib, Item):
                item = id_or_attrib
                if item not in self:
                    raise LookupError(f"no such item: {item!r}")
                item.update(attrib=attrs)
            elif isinstance(id_or_attrib, str):
                id = id_or_attrib
                item = super().get(id)
                if item is None:
                    if "href" in attrs:
                        href = attrs.pop("href")
                        self.add(href, id=id, attrib=attrs)
                    else:
                        raise LookupError(f"no such item: {id!r}")
                else:
                    item.update(attrs)
            else:
                self._proxy.update(id_or_attrib, **attrs)
        elif isinstance(id_or_attrib, Mapping):
            self._proxy.update(id_or_attrib)
        return self

    #################### SubElement Methods #################### 

    @PyLinq.streamify
    def filter(self, /, predicate=None):
        if not callable(predicate):
            return iter(self.values())
        return filter(predicate, self.values())

    @PyLinq.streamify
    def filter_by_attr(self, predicate=None, attr="media-type", /):
        def activate_predicate(predicate):
            if predicate is None:
                return None
            if callable(predicate):
                return predicate
            elif isinstance(predicate, Pattern):
                return predicate.search
            elif isinstance(predicate, str):
                use_false = False
                if predicate.startswith(r"!"):
                    use_false = True
                    predicate = predicate[1:]
                predicate_startswith = predicate.startswith
                if predicate_startswith(r"="):
                    predicate = predicate[1:].__eq__
                elif predicate_startswith(r"~"):
                    predicate = methodcaller("__contains__", predicate[1:])
                elif predicate_startswith(r"^"):
                    predicate = methodcaller("startswith", predicate[1:])
                elif predicate_startswith(r"$"):
                    predicate = methodcaller("endswith", predicate[1:])
                elif predicate_startswith(r";"):
                    predicate = lambda s, needle=predicate[1:]: needle in s.split()
                elif predicate_startswith(r","):
                    predicate = lambda s, needle=predicate[1:]: needle in s.split(",")
                elif predicate_startswith(r"<"):
                    predicate = re_compile(r"\b"+re_escape(predicate[1:])).search
                elif predicate_startswith(r">"):
                    predicate = re_compile(re_escape(predicate[1:])+r"\b").search
                elif predicate_startswith(r"|"):
                    predicate = re_compile(r"\b"+re_escape(predicate[1:])+r"\b").search
                elif predicate_startswith(r"*"):
                    predicate = re_compile(wildcard_translate(predicate[1:])).fullmatch
                elif predicate_startswith(r"/"):
                    predicate = re_compile(predicate[1:]).search
                elif predicate_startswith(r"%"):
                    predicate = re_compile(predicate[1:]).fullmatch
                else:
                    predicate = predicate.__eq__
                if use_false:
                    predicate = lambda s, _pred=predicate: not _pred(s)
                return predicate
            elif type(predicate) in (tuple, list):
                preds = tuple(pred for p in predicate if (pred:=activate_predicate(p)) is not None)
                if not preds:
                    return None
                if type(predicate) is tuple:
                    return lambda s, _preds=preds: any(p(s) for p in preds)
                else:
                    return lambda s, _preds=preds: all(p(s) for p in preds)
            elif isinstance(predicate, Container):
                return predicate.__contains__
        predicate = activate_predicate(predicate)
        if predicate is None:
            return filter(lambda item: attr in item, self.values())
        return filter(lambda item: attr in item and predicate(item[attr]), self.values())

    @PyLinq.streamify
    def iter(self, /):
        root = self._root
        for el in root.iterfind("*"):
            if not (el.tag == "item" or el.tag.endswith("}item")):
                yield ElementProxy(el)
                continue
            id = el.attrib.get("id")
            href = el.attrib.get("href")
            if not href:
                if id is None or not super().__contains__(id):
                    try:
                        root.remove(el)
                        warn(f"removed a dangling item element: {el!r}")
                    except:
                        pass
                else:
                    item = super().__getitem__(id)
                    if item._root is not el:
                        raise RuntimeError(f"different item elements {el!r} and {item._root!r} share the same id {id!r}")
                    else:
                        self.pop(id, None)
                        warn(f"removed an item because of missing href attribute: {item!r}")
                continue
            href = unquote(href)
            if not el.attrib.get("media-type"):
                el.attrib["media-type"] = guess_media_type(href)
            if id is None:
                yield self.add(href)
            elif super().__contains__(id):
                item = super().__getitem__(id)
                if item._root is not el:
                    raise RuntimeError(f"different item elements {el!r} and {item._root!r} share the same id {id!r}")
                yield item
            else:
                try:
                    self._root.remove(el)
                    warn(f"removed a dangling item element: {el!r}")
                except:
                    pass

    def list(self, /, mapfn=None):
        if mapfn is None:
            return list(self.iter())
        return list(map(mapfn, self.iter()))

    def audio_iter(self, /):
        return self.filter_by_attr("^audio/")

    def css_iter(self, /):
        return self.filter_by_attr("text/css")

    def font_iter(self, /):
        return self.filter_by_attr(("^font/", "^application/font-"))

    def image_iter(self, /):
        return self.filter_by_attr("^image/")

    def javascript_iter(self, /):
        return self.filter_by_attr(("text/javascript", "application/javascript", "application/ecmascript"))

    def media_iter(self, /):
        return self.filter_by_attr(("^audio/", "^image/", "^video/"))

    def text_iter(self, /):
        return self.filter_by_attr(("^text/", "$+xml"))

    def video_iter(self, /):
        return self.filter_by_attr("^video/")

    @PyLinq.streamify
    def html_spine_iter(self, /):
        for id, itemref in book.spine.items():
            yield book.manifest[id], itemref
        for item in book.manifest.filter_by_attr(("text/html", "application/xhtml+xml")) :
            yield item, None

    #################### File System Methods #################### 

    def add(
        self, 
        href, 
        /, 
        file=None, 
        fs=None, 
        open_modes="r", 
        id=None, 
        media_type=None, 
        attrib=None, 
    ):
        if isinstance(href, Item):
            raise TypeError("can't directly add `Item` object")
        if isinstance(href, (bytes, PathLike)):
            href = fsdecode(href)
        else:
            href = str(href)
        assert (href := href.strip("/")), "empty href"
        if href in self._href_to_id:
            raise FileExistsError(errno.EEXIST, f"file exists: {href!r}")
        uid = str(uuid4())
        if id is None:
            generate_id = self._epub._generate_id
            if generate_id is None:
                id = uid
            else:
                id = generate_id(href, self.keys())
        if id in self:
            raise LookupError(f"id already exists: {id!r}")
        attrib = dict(attrib) if attrib else {}
        attrib["id"] = id
        attrib["href"] = quote(href, safe=":/?&=#")
        if media_type:
            attrib["media-type"] = media_type
        if fs is not None:
            file = File(file, fs=fs, open_modes=open_modes)
        elif file is None:
            file = File(uid, self._workfs)
        elif isinstance(file, IOBase) or hasattr(file, "read") and not hasattr(file, "open"):
            file0 = file
            file = File(uid, self._workfs)
            test_data = file0.read(0)
            if test_data == b"":
                copyfileobj(file0, self._workfs.open(uid, "wb"))
            elif test_data == "":
                attrib.setdefault("media-type", "text/plain")
                copyfileobj(file0, self._workfs.open(uid, "w"))
            else:
                raise TypeError(f"incorrect read behavior: {file0!r}")
        else:
            file = File(file, open_modes=open_modes)
        if not attrib.get("media-type"):
            attrib["media-type"] = guess_media_type(href)
        item = Item(el_add(self._root, "item", attrib=attrib, namespaces=NAMESPACES), self)
        super().__setitem__(id, item)
        self._href_to_id[href] = id
        self._href_to_file[href] = file
        return item

    def exists(self, href, /):
        if isinstance(href, Item):
            return href in self
        if isinstance(href, (bytes, PathLike)):
            href = fsdecode(href)
        else:
            href = str(href)
        assert (href := href.strip("/")), "empty href"
        return href in self._href_to_id

    @PyLinq.streamify
    def glob(self, pattern="*", dirname="", ignore_case=False):
        pattern = pattern.strip("/")
        if not pattern:
            return
        if isinstance(dirname, Item):
            dirname = posixpath.dirname(unquote(href._attrib["href"]))
        else:
            dirname = dirname.strip("/")
        if dirname:
            dirname = re_escape(dirname)
        pattern = joinpath(dirname, *posix_glob_translate_iter(pattern))
        if ignore_case:
            pattern = "(?i:%s)" % pattern
        matches = re_compile(pattern).fullmatch
        for href, id in self._href_to_id.items():
            if not matches(href):
                continue
            try:
                yield super().__getitem__(id)
            except KeyError:
                pass

    @PyLinq.streamify
    def iterdir(self, /, dirname=""):
        if isinstance(dirname, Item):
            dirname = posixpath.dirname(unquote(href._attrib["href"]))
        else:
            dirname = dirname.strip("/")
        for href, id in self._href_to_id.items():
            if posixpath.dirname(href) != dirname:
                continue
            try:
                yield super().__getitem__(id)
            except KeyError:
                pass

    def open(
        self, 
        href, 
        /, 
        mode="r", 
        buffering=-1, 
        encoding=None, 
        errors=None, 
        newline=None, 
    ):
        if mode not in OPEN_MODES:
            raise ValueError(f"invalid open mode: {mode!r}")
        if isinstance(href, Item):
            if href not in self:
                raise LookupError(f"no such item: {href!r}")
            href = unquote(href["href"])
        else:
            if isinstance(href, (bytes, PathLike)):
                href = fsdecode(href)
            else:
                href = str(href)
            assert (href := href.strip("/")), "empty href"
        href_to_file = self._href_to_file
        if href in self._href_to_id:
            if "x" in mode:
                raise FileExistsError(errno.EEXIST, f"file exists: {href!r}")
            file = href_to_file.get(href)
            uid = str(uuid4())
            if file is None:
                href_to_file[href] = file = File(uid, self._workfs)
            elif not file.check_open_mode(mode):
                if "w" not in mode:
                    try:
                        fsrc = file.open("rb", buffering=0)
                    except FileNotFoundError:
                        if "r" in mode:
                            raise
                    else:
                        with fsrc:
                            copyfileobj(fsrc, self._workfs.open(uid, "wb"))
                href_to_file[href] = file = File(uid, self._workfs)
        elif "r" in mode:
            raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
        else:
            item = self.add(href)
            file = href_to_file[href]
        if "b" not in mode and encoding is None:
            encoding = "utf-8"
        return file.open(
            mode=mode, 
            buffering=buffering, 
            encoding=encoding, 
            errors=errors, 
            newline=newline, 
        )

    def read(self, href, /, buffering=0):
        with self.open(href, "rb", buffering=buffering) as f:
            return f.read()

    read_bytes = read

    def read_text(self, href, /, encoding=None):
        with self.open(href, "r", encoding=encoding) as f:
            return f.read()

    def remove(self, href, /):
        if isinstance(href, Item):
            if href not in self:
                raise LookupError(f"no such item: {href!r}")
            href = unquote(href["href"])
        else:
            if isinstance(href, (bytes, PathLike)):
                href = fsdecode(href)
            else:
                href = str(href)
            assert (href := href.strip("/")), "empty href"
        try:
            id = self._href_to_id.pop(href)
        except LookupError:
            raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
        item = super().pop(id, None)
        if item is not None:
            try:
                self._root.remove(item._root)
            except:
                pass
        file = self._href_to_file.pop(href, None)
        if file is not None and file.check_open_mode("w"):
            try:
                file.remove()
            except:
                pass

    def _rename(self, item, href, dest_href, /):
        try:
            id = self._href_to_id[dest_href] = self._href_to_id.pop(href)
        except LookupError:
            raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
        if item is None:
            item = super().__getitem__(id)
        item._attrib["href"] = quote(dest_href, safe=":/?&=#")
        self._href_to_file[dest_href] = self._href_to_file.pop(href, None)

    def rename(self, href, dest_href, /, repair=False):
        result = {}
        if isinstance(href, Item):
            item = href
            if item not in self:
                raise LookupError(f"no such item: {item!r}")
            href = unquote(item._attrib["href"])
        else:
            if isinstance(href, (bytes, PathLike)):
                href = fsdecode(href)
            else:
                href = str(href)
            assert (href := href.strip("/")), "empty href"
            item = None
        if isinstance(dest_href, (bytes, PathLike)):
            dest_href = fsdecode(dest_href)
        else:
            dest_href = str(dest_href)
        assert (dest_href := dest_href.strip("/")), "empty href"
        result["pathpair"] = (href, dest_href)
        if href != dest_href:
            if dest_href in self._href_to_id:
                raise FileExistsError(errno.EEXIST, f"target file exists: {dest_href!r}")
            self._rename(item, href, dest_href)
            if repair:
                result["repairs"] = remap_links(self, (href, dest_href))
        return result

    def batch_rename(self, mapper, /, predicate=None, repair=False):
        result = {}
        result["pathmap"] = pathmap = {}
        result["fails"] = fails = {}
        if not callable(mapper) and isinstance(mapper, Mapping):
            def mapper(item, m=mapper):
                href = unquote(item["href"])
                try:
                    return m[href]
                except LookupError:
                    return href
            if predicate is None:
                predicate = mapper
        if not callable(predicate) and isinstance(predicate, Mapping):
            predicate = lambda item, m=predicate: unquote(item["href"]) in m
        for item in self.filter(predicate):
            try:
                href, dest_href = self.rename(item, mapper(item))["pathpair"]
                if href != dest_href:
                    pathmap[href] = dest_href
            except Exception as e:
                fails[unquote(item._attrib["href"])] = e
        if pathmap and repair:
            result["repairs"] = remap_links(self, pathmap)
        return result

    def replace(self, href, dest_href, /):
        if isinstance(href, Item):
            item = href
            if item not in self:
                raise LookupError(f"no such item: {item!r}")
            href = unquote(item._attrib["href"])
        else:
            if isinstance(href, (bytes, PathLike)):
                href = fsdecode(href)
            else:
                href = str(href)
            assert (href := href.strip("/")), "empty href"
            if href not in self._href_to_id:
                raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
            item = None
        if isinstance(dest_href, Item):
            dest_item = dest_href
            if dest_item not in self:
                raise LookupError(f"no such item: {dest_item!r}")
            dest_href = unquote(dest_item["href"])
        else:
            if isinstance(dest_href, (bytes, PathLike)):
                dest_href = fsdecode(dest_href)
            else:
                dest_href = str(dest_href)
            assert (dest_href := dest_href.strip("/")), "empty href"
            dest_item = None
        if href == dest_href:
            return
        if dest_item is not None:
            del self[dest_item]
        elif dest_href in self._href_to_id:
            del self[self._href_to_id[dest_href]]
        self._rename(item, href, dest_href)

    def rglob(self, pattern="", dirname="", ignore_case=False):
        if pattern:
            pattern = joinpath("**", pattern.lstrip("/"))
        else:
            pattern = "**"
        return self.glob(pattern, dirname, ignore_case)

    def stat(self, href, /) -> Optional[stat_result]:
        if isinstance(href, Item):
            if href not in self:
                raise LookupError(f"no such item: {href!r}")
            href = unquote(href["href"])
        else:
            if isinstance(href, (bytes, PathLike)):
                href = fsdecode(href)
            else:
                href = str(href)
            assert (href := href.strip("/")), "empty href"
            if href not in self._href_to_id:
                raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
        try:
            stat = self._href_to_file[href].stat
        except (AttributeError, LookupError):
            return None
        if callable(stat):
            return stat()
        return None

    def touch(self, href, /):
        try:
            self.open(href, "rb", buffering=0).close()
        except:
            self.open(href, "wb", buffering=0).close()

    unlink = remove

    def write(self, href, /, data):
        need_close = True
        if isinstance(data, File):
            fsrc = data.open("rb", buffering=0)
        elif callable(getattr(data, "read", None)):
            fsrc = data
            need_close = False
        elif isinstance(data, (str, PathLike)):
            fsrc = open(data, "rb", buffering=0)
        else:
            content = memoryview(data)
            with self.open(href, "wb") as f:
                return f.write(content)
        try:
            fsrc_read = fsrc.read
            test_data = fsrc_read(0)
            if test_data == "":
                fsrc_read = lambda n, read=fsrc_read: bytes(read(n), "utf-8")
            elif test_data:
                raise TypeError(f"incorrect read behavior: {fsrc!r}")
            with self.open(href, "wb") as fdst:
                fdst_write = fdst.write
                n = 0
                while (buf := fsrc_read(1 << 16)):
                    n += fdst_write(buf)
                return n
        finally:
            if need_close:
                fsrc.close()

    write_bytes = write

    def write_text(self, href, /, text, encoding=None, errors=None, newline=None):
        with self.open(href, "w", encoding=encoding, errors=errors, newline=newline) as f:
            return f.write(text)


class SpineProxy(ElementAttribProxy):
    __optional_keys__ = ("id", "page-progression-direction")


class Spine(dict[str, Itemref]):

    def __init__(self, root: Element, /, manifest: Manifest):
        self._root = root
        self._attrib = root.attrib
        self._proxy = SpineProxy(root)
        self._manifest = manifest
        if len(root):
            dangling_itemrefs = []
            for itemref in root.iterfind("{*}itemref"):
                idref = itemref.attrib.get("idref")
                if idref is None or idref not in manifest:
                    dangling_itemrefs.append(itemref)
                    continue
                super().__setitem__(cast(str, idref), Itemref(itemref))
            if dangling_itemrefs:
                for itemref in reversed(dangling_itemrefs):
                    warn(f"removed a dangling item element: {itemref!r}")
                    root.remove(itemref)

    def __init_subclass__(self, /, **kwargs):
        raise TypeError("subclassing is not allowed")

    def __call__(self, id, /, attrib=None):
        if isinstance(id, Item):
            id = id._attrib["id"]
        if isinstance(id, Itemref):
            if id not in self:
                raise LookupError(f"no such itemref: {id!r}")
            itemref = id
        else:
            itemref = super().get(id)
        if not attrib:
            return itemref
        if itemref is None:
            if id not in self._manifest:
                raise LookupError(f"no such item: {id!r}")
            itemref = self._add(id, attrib)
        else:
            itemref.update(attrib)
        return itemref

    def __contains__(self, id, /):
        if isinstance(id, Itemref):
            return super().get(id._attrib["idref"]) is id
        return super().__contains__(id)

    def __delitem__(self, key, /):
        pop = self.pop
        if isinstance(key, Itemref):
            if key not in self:
                raise LookupError(f"no such itemref: {key!r}")
            key = key._attrib["idref"]
        elif isinstance(key, Item):
            key = key._attrib["id"]
        if isinstance(key, str):
            pop(key, None)
        elif isinstance(key, int):
            el = self._root[key]
            try:
                id = el.attrib["idref"]
            except AttributeError:
                try:
                    self._root.remove(el)
                except:
                    pass
            else:
                pop(id)
        elif isinstance(key, slice):
            root = self._root
            for el in root[key]:
                try:
                    id = el.attrib["idref"]
                except AttributeError:
                    try:
                        root.remove(el)
                    except:
                        pass
                else:
                    pop(id, None)
        else:
            raise TypeError("`key` only accepts: `str`, `int`, `slice`, `Item`, `Itemref`")
        return self

    def __getitem__(self, key, /):
        def wrap(el):
            try:
                if el.tag == "itemref" or el.tag.endswith("}itemref"):
                    return Itemref(el)
                return ElementProxy(el)
            except AttributeError:
                return el
        if isinstance(key, Itemref):
            if key not in self:
                raise LookupError(f"no such itemref: {key!r}")
            return key
        if isinstance(key, Item):
            key = key._attrib["id"]
        if isinstance(key, str):
            return super().__getitem__(key)
        elif isinstance(key, int):
            return wrap(self._root[key])
        elif isinstance(key, slice):
            return list(map(wrap, self._root[key]))
        else:
            raise TypeError("`key` only accepts: `str`, `int`, `slice`, `Item`, `Itemref`")

    def __setitem__(self, id, attrib, /):
        if isinstance(key, Item):
            key = key._attrib["id"]
        if isinstance(key, Itemref):
            if key not in self:
                raise LookupError(f"no such itemref: {key!r}")
            itemref = key
        else:
            itemref = super().get(id)
        if itemref is None:
            self.add(key, attrib=attrib)
        else:
            itemref.update(attrib)
        return self

    @property
    def attrib(self, /):
        return self._attrib

    @property
    def manifest(self, /):
        return self._manifest

    @property
    def proxy(self, /):
        return self._proxy

    @property
    def info(self, /):
        return tuple(itemref.info for itemref in self.values())

    delete = __delitem__

    def _add(self, id, /, attrib=None):
        if attrib:
            attrib = dict(attrib, idref=id)
        else:
            attrib = {"idref": id}
        itemref = Itemref(el_add(self._root, "itemref", attrib=attrib, namespaces=NAMESPACES))
        super().__setitem__(id, itemref)
        return itemref

    def add(self, id, /, attrib=None):
        if isinstance(id, Itemref):
            raise TypeError("can't directly add `Itemref` object")
        if isinstance(id, Item):
            id = id._attrib["id"]
        elif id not in self._manifest:
            raise LookupError(f"no such id in manifest: {id!r}")
        if super().__contains__(id):
            raise LookupError(f"id already exists: {id!r}")
        return self._add(id, attrib)

    def clear(self, /):
        self._root.clear()
        super().clear()
        return self

    @PyLinq.streamify
    def iter(self, /):
        root = self._root
        for el in root.iterfind("*"):
            if not (el.tag == "itemref" or el.tag.endswith("}itemref")):
                yield ElementProxy(el)
                continue
            idref = el.attrib.get("idref")
            if idref is None or idref not in self._manifest:
                try:
                    root.remove(el)
                    warn(f"removed a dangling itemref element: {el!r}")
                except:
                    pass
            elif idref not in self:
                itemref = self._add(idref)
                yield itemref
            else:
                itemref = self[idref]
                if itemref._root is not el:
                    raise RuntimeError(f"different itemref elements {el!r} and {itemref._root!r} share the same id {idref!r}")
                yield itemref

    def list(self, /, mapfn=None):
        if mapfn is None:
            return list(self.iter())
        return list(map(mapfn, self.iter()))

    def pop(self, id, /, default=undefined):
        if isinstance(id, Item):
            id = id._attrib["id"]
        if isinstance(id, Itemref):
            if id not in self:
                if default is undefined:
                    raise LookupError(f"no such itemref: {id!r}")
                return default
            itemref = id
            super().__delitem__(itemref._attrib["idref"])
        else:
            if id not in self:
                if default is undefined:
                    raise LookupError(f"no such itemref: {id!r}")
                return default
            itemref = super().pop(id)
        try:
            self._root.remove(itemref._root)
        except:
            pass
        return itemref

    def popitem(self, /):
        id, itemref = super().popitem()
        try:
            self._root.remove(itemref._root)
        except:
            pass
        return id, itemref

    def set(self, id, /, attrib=None):
        if isinstance(id, Item):
            id = id._attrib["id"]
        if isinstance(id, Itemref):
            if id not in self:
                raise LookupError(f"no such itemref: {id!r}")
            itemref = id
        else:
            itemref = super().get(id)
        if itemref is None:
            return self.add(id, attrib)
        itemref.update(attrib)
        return itemref

    def setdefault(self, id, /, attrib=None):
        if isinstance(id, Item):
            id = id._attrib["id"]
        if isinstance(id, Itemref):
            if id not in self:
                raise LookupError(f"no such itemref: {id!r}")
            itemref = id
        else:
            itemref = super().get(id)
        if itemref is None:
            return self.add(id, attrib)
        itemref.merge(attrib)
        return itemref

    def merge(self, id_or_attrib=None, /, **attrs):
        if isinstance(id_or_attrib, Item):
            id_or_attrib = id_or_attrib._attrib["id"]
        if attrs:
            if isinstance(id_or_attrib, Itemref):
                itemref = id_or_attrib
                if itemref not in self:
                    raise LookupError(f"no such itemref: {itemref!r}")
                itemref.merge(attrs)
            elif isinstance(id_or_attrib, str):
                id = id_or_attrib
                itemref = super().get(id)
                if itemref is None:
                    self.add(id, attrs)
                else:
                    itemref.merge(attrs)
            else:
                self._proxy.merge(id_or_attrib, **attrs)
        elif isinstance(id_or_attrib, Mapping):
            self._proxy.merge(id_or_attrib)
        return self

    def update(self, id_or_attrib=None, /, **attrs):
        if isinstance(id_or_attrib, Item):
            id_or_attrib = id_or_attrib._attrib["id"]
        if attrs:
            if isinstance(id_or_attrib, Itemref):
                itemref = id_or_attrib
                if itemref not in self:
                    raise LookupError(f"no such itemref: {itemref!r}")
                itemref.update(attrs)
            elif isinstance(id_or_attrib, str):
                id = id_or_attrib
                itemref = super().get(id)
                if itemref is None:
                    self.add(id, attrs)
                else:
                    itemref.update(attrs)
            else:
                self._proxy.update(id_or_attrib, **attrs)
        elif isinstance(id_or_attrib, Mapping):
            self._proxy.update(id_or_attrib)
        return self


class ePub(ElementProxy):
    __protected_keys__ = ("unique-identifier", "version")
    __optional_keys__ = ("dir", "id", "prefix", "xml:lang")
    __cache_get_key__ = False

    def __init__(self, /, path=None, workroot=None, maketemp=True, generate_id=None):
        if path and ospath.lexists(path):
            self._zfile = zfile = ZipFile(path)
            contenter_xml = zfile.read("META-INF/container.xml")
            match = fromstring(contenter_xml).find(
                '{*}rootfiles/{*}rootfile[@media-type="application/oebps-package+xml"][@full-path]', 
            )
            if match is None:
                raise FileNotFoundError(errno.ENOENT, "no opf file specified in container.xml")
            self._opf_path = opf_path = unquote(match.attrib["full-path"])
            self._opf_dir, self._opf_name = opf_dir, _ = posixpath.split(opf_path)
            root = fromstring(zfile.read(opf_path))
        else:
            self._opf_path = "OEBPS/content.opf"
            self._opf_dir = "OEBPS"
            self._opf_name = "content.opf"
            root = fromstring(b'''\
<?xml version="1.0" encoding="utf-8"?>
<package version="3.3" unique-identifier="BookId" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="BookId" opf:scheme="UUID">urn:uuid:%(uuid)s</dc:identifier>
    <dc:language>en</dc:language>
    <dc:title></dc:title>
    <meta property="dcterms:modified">%(mtime)s</meta>
  </metadata>
  <manifest />
  <spine />
</package>''' % {
    b"uuid": bytes(str(uuid4()), "utf-8"), 
    b"mtime": bytes(datetime.now().strftime("%FT%XZ"), "utf-8"), 
})
        super().__init__(root)
        self._path = path
        self._workroot = workroot
        self._maketemp = maketemp
        if generate_id is None:
            self._generate_id = None
        else:
            try:
                argcount = generate_id.__code__.co_argcount
            except AttributeError:
                argcount = len(getfullargspec(generate_id).args)
            if argcount == 0:
                self._generate_id = lambda href, seen_ids: generate_id()
            elif argcount == 1:
                self._generate_id = lambda href, seen_ids: generate_id(href)
            else:
                self._generate_id = generate_id
        self.metadata
        self.manifest
        self.spine

    def __del__(self):
        try:
            self._zfile.close()
        except:
            pass

    def __getattr__(self, attr, /):
        return getattr(self.manifest, attr)

    @cached_property
    def metadata(self, /):
        return Metadata(el_set(self._root, "{*}metadata", "metadata", attrib={
            "xmlns:dc": "http://purl.org/dc/elements/1.1/", 
            "xmlns:opf": "http://www.idpf.org/2007/opf", 
        }))

    @cached_property
    def manifest(self, /):
        return Manifest(el_set(self._root, "{*}manifest", "manifest"), self)

    @cached_property
    def spine(self, /):
        return Spine(el_set(self._root, "{*}spine", "spine"), self.manifest)

    @property
    def info(self, /):
        return MappingProxyType({
            "metadata": MappingProxyType({"attrib": self.metadata.attrib, "children": self.metadata.info}), 
            "manifest": MappingProxyType({"attrib": self.manifest.attrib, "children": self.manifest.info}), 
            "spine": MappingProxyType({"attrib": self.spine.attrib, "children": self.spine.info}), 
        })

    @proxy_property # type: ignore
    def identifier(self, /):
        uid = self.get("unique-identifier")
        text = lambda: f"urn:uuid:{uuid4()}"
        if uid:
            return self.metadata.dc("identifier", find_attrib={"id": uid}, text=text, merge=True, auto_add=True)
        else:
            return self.metadata.dc("identifier", text=text, merge=True, auto_add=True)

    @identifier.setter # type: ignore
    def identifier(self, text, /):
        uid = self.get("unique-identifier")
        if uid:
            self.metadata.dc("identifier", find_attrib={"id": uid}, text=text, auto_add=True)
        else:
            self.metadata.dc("identifier", text=text, auto_add=True)

    @proxy_property # type: ignore
    def language(self, /):
        return self.metadata.dc("language", text="en", merge=True, auto_add=True)

    @language.setter # type: ignore
    def language(self, text, /):
        self.metadata.dc("language", text=text, auto_add=True)

    @proxy_property # type: ignore
    def title(self, /):
        return self.metadata.dc("title", text="", merge=True, auto_add=True)

    @title.setter # type: ignore
    def title(self, text, /):
        self.metadata.dc("title", text=text, auto_add=True)

    @proxy_property
    def modification_time(self, /):
        return self.metadata.meta(
            find_attrib={"property": "dcterms:modified"}, 
            text=lambda: datetime.now().strftime("%FT%XZ"), 
            auto_add=True, 
            merge=True, 
        )

    def mark_modified(self, /):
        self.metadata.dc('date[@opf:event="modification"]', text=lambda: datetime.now().strftime("%F"))
        return self.metadata.meta(
            find_attrib={"property": "dcterms:modified"}, 
            text=lambda: datetime.now().strftime("%FT%XZ"), 
            auto_add=True, 
        ).text

    @property
    def cover(self, /):
        for item in self.manifest.filter_by_attr("cover-image", "properties"):
            return item
        cover_meta = self.metadata.name_meta("cover")
        if cover_meta is None:
            return None
        cover_id = cover_meta.get("content")
        return self.manifest.get(cover_id)

    @property
    def toc(self, /):
        for item in self.manifest.filter_by_attr(";nav", "properties"):
            return item
        toc_id = self.spine.attrib.get("toc")
        if toc_id is None:
            return None
        return self.manifest.get(toc_id)

    @property
    def creators(self, /):
        return tuple(self.metadata.iterfind("dc:creator"))

    def add_creator(self, creator, attrib=None, file_as=None, role=None):
        dcterm = self.metadata.add("dc:creator", attrib=attrib, text=creator)
        id = dcterm.get("id")
        if id is None and not (file_as is role is None):
            id = str(uuid4())
            dcterm["id"] = id
        if file_as is not None:
            self.metadata.add(text=file_as, attrib={
                "refines": f"#{id}", 
                "property": "file-as", 
                "scheme": "marc:relators", 
            })
        if role is not None:
            self.metadata.add(text=role, attrib={
                "refines": f"#{id}", 
                "property": "role", 
                "scheme": "marc:relators", 
            })
        return dcterm

    def namelist(self, /):
        opf_dir = self._opf_dir
        zfile = self.__dict__.get("_zfile")
        namelist = [joinpath(opf_dir, href) for href in self.manifest.href_to_id]
        namelist.append(self._opf_path)
        if zfile is None:
            namelist.append("mimetype")
            namelist.append("META-INF/container.xml")
        else:
            exclude_files = set(namelist)
            exclude_files.update(
                normpath(joinpath(opf_dir, unquote(item.attrib["href"])))
                for item in fromstring(zfile.read(self._opf_path)).find("{*}manifest")
            )
            namelist.extend(name for name in zfile.NameToInfo if name not in exclude_files)
        return namelist

    def pack(
        self, 
        /, 
        path=None, 
        compression=ZIP_STORED, 
        allowZip64=True, 
        compresslevel=None, 
        extra_files=None, 
    ):
        if not path and not self._path:
            raise OSError(errno.EINVAL, "please specify a path to save")
        opf_dir, opf_name, opf_path = self._opf_dir, self._opf_name, self._opf_path
        href_to_id = self.manifest.href_to_id
        href_to_file = self.manifest.href_to_file
        def write_extra_files(wfile, extra_files):
            if extra_files:
                if isinstance(extra_files, Mapping):
                    extra_files = items(extra_files)
                for name, file in extra_files:
                    if name in exclude_files:
                        continue
                    exclude_files.add(name)
                    if file is None or file == "":
                        continue
                    if hasattr(file, "read"):
                        with wfile.open(name, "w") as fdst:
                            copyfileobj(file, fdst)
                    elif isinstance(file, (str, Pathlike)):
                        wfile.write(file, name)
                    else:
                        content = memoryview(file)
                        wfile.writestr(name, content)
        def write_oebps(wfile):
            bad_ids = set()
            good_ids = set()
            for href, id in href_to_id.items():
                if href == opf_name:
                    bad_ids.add(id)
                    warn(f"ignore a file, because its href conflicts with OPF: {opf_name!r}")
                    continue
                file = href_to_file.get(href)
                if file is None:
                    bad_ids.add(id)
                    warn(f"ignore a file, because it has never been actually created: {href!r}")
                    continue
                try:
                    fsrc = file.open("rb", buffering=0)
                except (OSError, LookupError) as e:
                    bad_ids.add(id)
                    warn(f"can't open {href!r}\n    |_ {type(e).__qualname__}: {e}")
                else:
                    try:
                        with wfile.open(joinpath(opf_dir, href), "w") as fdst:
                            copyfileobj(fsrc, fdst)
                        good_ids.add(id)
                    finally:
                        fsrc.close()
            self.mark_modified()
            root = self._root
            if bad_ids:
                root = deepcopy(root)
                manifest = root.find("{*}manifest")
                manifest[:] = (item for item in manifest.iterfind("{*}item[@id]") if item._attrib["id"] in good_ids)
            wfile.writestr(opf_path, tostring(root, encoding="utf-8", xml_declaration=True))
        zfile = self.__dict__.get("_zfile")
        exclude_files = {joinpath(opf_dir, href) for href in href_to_id}
        exclude_files.add(opf_path)
        if zfile is None:
            if path is None:
                path = self._path
            with ZipFile(path, "w", compression, allowZip64, compresslevel) as wfile:
                write_extra_files(wfile, extra_files)
                if "mimetype" not in exclude_files:
                    wfile.writestr("mimetype", b"application/epub+zip")
                if "META-INF/container.xml" not in exclude_files:
                    wfile.writestr("META-INF/container.xml", b'''\
<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
   </rootfiles>
</container>''')
                write_oebps(wfile)
        else:
            if path is None or path == self._path:
                raise ValueError(f"not allowed to overwrite the original file: {self._path!r}")
            with ZipFile(path, "w", compression, allowZip64, compresslevel) as wfile:
                write_extra_files(wfile, extra_files)
                exclude_files.update(
                    normpath(joinpath(opf_dir, unquote(item.attrib["href"])))
                    for item in fromstring(zfile.read(opf_path)).find("{*}manifest")
                )
                for name, info in zfile.NameToInfo.items():
                    if info.is_dir() or name in exclude_files:
                        continue
                    with zfile.open(name) as fsrc, wfile.open(name, "w") as fdst:
                        copyfileobj(fsrc, fdst)
                write_oebps(wfile)

