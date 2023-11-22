#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io>"
__version__ = (0, 0, 1)
__all__ = ["ePub", "Metadata", "Manifest", "Item", "Spine", "Itemref"]

import errno
import io
import os
import os.path as ospath
import posixpath

from copy import deepcopy
from datetime import datetime
from fnmatch import translate as wildcard_translate
from functools import cached_property, partial
from inspect import isclass
from io import IOBase, TextIOWrapper
from operator import methodcaller
from os import fsdecode, remove, stat, stat_result, PathLike
from pathlib import PurePosixPath
from posixpath import join as joinpath
from pprint import pformat
from re import compile as re_compile, escape as re_escape, Pattern
from shutil import copy, copyfileobj
from tempfile import TemporaryDirectory
from typing import cast, Any, Callable, Mapping, MutableMapping, Optional
from types import MappingProxyType
from uuid import uuid4
from warnings import warn
from weakref import WeakKeyDictionary, WeakValueDictionary
from zipfile import ZipFile, ZIP_DEFLATED

from .util.file import File, OPEN_MODES
from .util.helper import guess_media_type, items
from .util.proxy import ElementAttribProxy, ElementProxy, NAMESPACES
from .util.stream import PyLinq
from .util.xml import el_add, el_del, el_iterfind, el_set
from .util.undefined import undefined, UndefinedType

try:
    from lxml.etree import fromstring, tostring, _Element as Element, _ElementTree as ElementTree # type: ignore
except ModuleNotFoundError:
    from xml.etree.ElementTree import fromstring, tostring, Element, ElementTree # type: ignore


TemporaryDirectory.__del__ = TemporaryDirectory.cleanup # type: ignore


class Item(ElementAttribProxy):
    __const_keys__ = ("id",)
    __protected_keys__ = ("href", "media-type")
    __cache_get_state__ = lambda _, manifest: manifest

    def __init__(self, root: Element, manifest, /):
        super().__init__(root)
        self._manifest = manifest

    def __eq__(self, other, /):
        if type(self) is not type(other):
            return NotImplemented
        return self._manifest is other._manifest and self.href == other.href

    def __fspath__(self, /):
        return self.href

    def __hash__(self, /):
        return hash((self._root, id(self._manifest)))

    def __setitem__(self, key, val, /):
        if key == "href":
            self.rename(val)
        else:
            super().__setitem__(key, val)
        return self

    @property
    def filename(self, /):
        return joinpath(self.home, self.href)

    @property
    def id(self, /):
        return self._attrib["id"]

    @property
    def href(self, /):
        return self._attrib["href"]

    @href.setter
    def href(self, href_new, /):
        self.rename(href_new)

    @property
    def media_type(self, /):
        return self._attrib["media-type"]

    @media_type.setter
    def media_type(self, value, /):
        if not value:
            self._attrib["media-type"] = guess_media_type(self._attrib["href"])
        else:
            self._attrib["media-type"] = value

    @property
    def home(self, /):
        return self._manifest._epub._opf_dir

    @property
    def name(self, /):
        return self.path.name

    @property
    def path(self, /):
        return PurePosixPath(self.href)

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
        return self.parent.joinpath(*others)

    __truediv__ = joinpath

    def relpath(self, other, /):
        return PurePosixPath(posixpath.relpath(other, posixpath.dirname(self.href)))

    def relative_to(self, /, *other):
        return self.path.relative_to(*other)

    def with_name(self, /, name):
        return self.path.with_name(name)

    def with_stem(self, /, stem):
        return self.path.with_stem(stem)

    def with_suffix(self, /, suffix):
        return self.path.with_suffix(suffix)

    def exists(self, /):
        return self._manifest.exists(self.href)

    def is_file(self, /):
        return self.exists()

    def is_dir(self, /):
        return False

    def is_symlink(self, /):
        return False

    def glob(self, /, pattern="*", ignore_case=False):
        return self._manifest.glob(pattern, posixpath.dirname(self.href), ignore_case=ignore_case)

    def rglob(self, /, pattern="", ignore_case=False):
        return self._manifest.rglob(pattern, posixpath.dirname(self.href), ignore_case=ignore_case)

    def iterdir(self, /):
        return self._manifest.iterdir(posixpath.dirname(self.href))

    def match(self, /, path_pattern, ignore_case=False):
        path_pattern = path_pattern.strip("/")
        if not path_pattern:
            return False
        pattern = joinpath(*posix_glob_translate_iter(path_pattern))
        if ignore_case:
            pattern = "(?i:%s)" % pattern
        return re_compile(pattern).fullmatch(self.href) is not None

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
            self.href, 
            mode=mode, 
            buffering=buffering, 
            encoding=encoding, 
            errors=errors, 
            newline=newline, 
        )

    def read(self, /):
        return self._manifest.read(self.href)

    read_bytes = read

    def read_text(self, /, encoding=None):
        return self._manifest.read(self.href, encoding=encoding)

    def remove(self, /):
        self._manifest.remove(self.href)
        return self

    def rename(self, href_new, /):
        self._manifest.rename(self.href, href_new)
        return self

    def replace(self, href, /):
        self._manifest.replace(self.href, href)
        return self

    def stat(self, /) -> Optional[stat_result]:
        return self._manifest.stat(self.href)

    def touch(self, /):
        self._manifest.touch(self.href)
        return self

    unlink = remove

    def write(self, /, data):
        return self._manifest.write(self.href, data)

    write_bytes = write

    def write_text(self, /, text, encoding=None, errors=None, newline=None):
        return self._manifest.write_text(self.href, text, encoding=encoding, errors=errors, newline=newline)


class Itemref(ElementAttribProxy):
    __const_keys__ = ("idref",)

    @property
    def idref(self, /):
        return self._attrib["idref"]

    @property
    def linear(self, /):
        return "no" if self._attrib.get("linear") == "no" else "yes"

    @linear.setter
    def linear(self, value, /):
        self._attrib["linear"] = "no" if value == "no" else "yes"


class Metadata(ElementProxy):

    def __repr__(self, /):
        attrib = self._attrib or ""
        return f"<{self.tag}>{attrib}\n{pformat(self.iter().list())}"

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


class Manifest(dict[str, Item]):

    def __init__(self, /, root: Element, epub):
        self._root = root
        self._attrib = root.attrib
        self._epub = epub
        self._proxy = ElementAttribProxy(root)
        self._href_to_id: dict[str, str] = {}
        self._href_to_file: dict[str, File] = {}
        if len(root):
            href_to_id = self._href_to_id
            has_dangling = False
            for item in root.iterfind("*"):
                try:
                    id = cast(str, item.attrib["id"])
                    href = cast(str, item.attrib["href"])
                except LookupError:
                    has_dangling = True
                    continue
                else:
                    super().__setitem__(id, Item(item, self))
                    href_to_id[href] = id
            if has_dangling:
                root[:] = (item._root for item in self.values()) # type: ignore
            zfile = epub.__dict__.get("_zfile")
            opf_dir = epub._opf_dir
            if zfile:
                href_to_file = self._href_to_file
                for href in href_to_id:
                    zpath = joinpath(opf_dir, href)
                    zinfo = zfile.NameToInfo.get(zpath)
                    if not zinfo or zinfo.is_dir():
                        warn(f"missing file in original epub: {href!r}")
                        href_to_file[href] = File(joinpath(self._workdir.name, str(uuid4())))
                    else:
                        href_to_file[href] = File(zpath, zfile)

    def __call__(self, href, /):
        try:
            id = self._href_to_id[href]
        except LookupError:
            raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
        return self[id]

    def __contains__(self, other, /):
        if isinstance(other, Item):
            return other._manifest is self and other.id in self
        return super().__contains__(other)

    def __del__(self, /):
        try:
            self.__dict__["_workdir"].cleanup()
        except:
            pass

    def __delitem__(self, key, /):
        pop = self.pop
        if isinstance(key, Item):
            key = key.id
        if isinstance(key, str):
            pop(key, None)
        elif isinstance(key, int):
            el = self._root[key]
            pop(el.attrib["id"], None)
        elif isinstance(key, slice):
            for el in self._root[key]:
                pop(el.attrib["id"], None)
        else:
            super().__delitem__(self, key)
        return self

    def __getitem__(self, key, /):
        if isinstance(key, Item):
            key = key.id
        if isinstance(key, int):
            return Item(self._root[key], self)
        elif isinstance(key, slice):
            return [Item(el, self) for el in self._root[key]]
        else:
            return super().__getitem__(key)

    def __setitem__(self, id, value, /):
        if isinstance(id, Item):
            id = id.id
        if id not in self:
            raise LookupError(f"no such item id: {id!r}")
        if isinstance(value, str):
            self.rename(self[id].href, href)
        elif isinstance(value, bytes):
            self.write(self[id].href, value)
        elif isinstance(value, PathLike):
            self._href_to_file[self[id].href] = File(value)
        elif isinstance(value, Mapping):
            self[id].update(value)
        else:
            raise TypeError("only `bytes`, `str`, `os.PathLike` and `typing.Mapping` are accecptable")
        return self

    @cached_property
    def _workdir(self, /):
        return TemporaryDirectory(self._epub._tempdir)

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

    def clear(self, /):
        self._root.clear()
        self._href_to_file.clear()
        self._href_to_id.clear()
        super().clear()
        return self

    def pop(self, id, /, default=undefined):
        if isinstance(id, Item):
            id = id.id
        if id not in self:
            if default is undefined:
                raise LookupError(f"no such item id: {id!r}")
            return default
        item = super().pop(id)
        try:
            self._root.remove(item._root)
        except:
            pass
        href = item.href
        self._href_to_id.pop(href, None)
        file = self._href_to_file.pop(href, None)
        if file and file.check_open_mode("w"):
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
        href = item.href
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
            id = id.id
        if isinstance(value, str):
            href = value
            if id in self:
                item = self[id]
                self.rename(item.href, href)
                return item
            else:
                return self.add(href, id=id)
        elif isinstance(value, bytes):
            if id not in self:
                raise LookupError(f"no such item id: {id!r}")
            item = self[id]
            self.write(item.href, value)
            return item
        elif isinstance(value, PathLike):
            if id not in self:
                raise LookupError(f"no such item id: {id!r}")
            item = self[id]
            self._href_to_file[item.href] = File(value)
            return item
        elif isinstance(value, Mapping):
            if id in self:
                return self[id].update(value)
            else:
                return self.add(attrib["href"], id=id, attrib=attrib)
        else:
            raise TypeError("only `bytes`, `str`, `os.PathLike` and `typing.Mapping` are accecptable")

    def setdefault(self, id, value, /):
        if isinstance(id, Item):
            id = id.id
        if isinstance(value, str):
            try:
                return self[id]
            except LookupError:
                return self.add(value, id=id)
        elif isinstance(value, Mapping):
            try:
                return self[id].merge(value)
            except LookupError:
                return self.add(attrib["href"], id=id, attrib=attrib)
        else:
            raise TypeError("only `str` and `typing.Mapping` are accecptable")

    def merge(self, id_or_attrib=None, /, **attrs):
        if isinstance(id_or_attrib, Item):
            id_or_attrib = id_or_attrib.id
        if isinstance(id_or_attrib, str):
            id = id_or_attrib
            if id in self:
                if attrs:
                    self[id].merge(attrs)
            elif "href" in attrs:
                href = attrs.pop("href")
                self.add(href, attrib=attrs)
            else:
                raise LookupError(f"no such item id: {id!r}")
        else:
            self._proxy.merge(id_or_attrib, **attrs)
        return self

    def update(self, id_or_attrib=None, /, **attrs):
        if isinstance(id_or_attrib, Item):
            id_or_attrib = id_or_attrib.id
        if isinstance(id_or_attrib, str):
            id = id_or_attrib
            if id in self:
                if attrs:
                    self[id].update(attrs)
            elif "href" in attrs:
                href = attrs.pop("href")
                self.add(href, attrib=attrs)
            else:
                raise LookupError(f"no such item id: {id!r}")
        else:
            self._proxy.update(id_or_attrib, **attrs)
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
                    return lambda s, _preds=preds: all(p(s) for p in preds)
                else:
                    return lambda s, _preds=preds: any(p(s) for p in preds)
        predicate = activate_predicate(predicate)
        if predicate is None:
            return filter(lambda item: attr in item, self.values())
        return filter(lambda item: attr in item and predicate(item[attr]), self.values())

    @PyLinq.streamify
    def iter(self, /):
        for el in self._root.iterfind("{*}item"):
            id = el.attrib.get("id")
            href = el.attrib.get("href")
            if not href:
                if id is None or id not in self:
                    try:
                        self._root.remove(el)
                        raise RuntimeError(f"removed a dangling item element: {el!r}")
                    except:
                        pass
                else:
                    item = self[id]
                    if item._root is not el:
                        raise RuntimeError(f"different item elements {el!r} and {item._root!r} share the same id {id!r}")
                    else:
                        self.pop(id, None)
                        warn(f"removed an item because of missing href attribute: {item!r}")
                continue
            if not el.attrib.get("media-type"):
                el.attrib["media-type"] = guess_media_type(href)
            if id is None:
                id = str(uuid4())
                item = Item(el, self)
                super().__setitem__(id, item)
                self._href_to_id[href] = id
                self._href_to_file[href] = File(ospath.join(self._workdir.name, id))
                yield item
            elif id in self:
                item = self[id]
                if item._root is not el:
                    raise RuntimeError(f"different item elements {el!r} and {item._root!r} share the same id {id!r}")
                yield item
            else:
                try:
                    self._root.remove(el)
                    raise RuntimeError(f"removed a dangling item element: {el!r}")
                except:
                    pass

    def sort(self, key=id, reverse=False, use_backend_element=False):
        if use_backend_element:
            self._root[:] = sorted(self._root.iterfind("{*}item[@id][@href]"), key=key, reverse=reverse)
        else:
            self._root[:] = (e._root for e in sorted(self.iter(), key=key, reverse=reverse))
        return self

    #################### File System Methods #################### 

    def add(self, href, /, file=None, fs=None, open_modes=None, id=None, media_type=None, attrib=None):
        assert (href := href.strip("/"))
        if href in self._href_to_id:
            raise FileExistsError(errno.EEXIST, f"file exists: {href!r}")
        uid = str(uuid4())
        if id is None:
            id = uid
        elif id in self:
            raise LookupError(f"id already exists: {id!r}")
        attrib = dict(attrib) if attrib else {}
        attrib["id"] = id
        attrib["href"] = href
        if not media_type:
            media_type = attrib.get("media-type")
            if not media_type:
                media_type = attrib["media-type"] = guess_media_type(href)
        if fs is not None:
            file = File(file, fs=fs, open_modes=open_modes)
        elif file is None:
            file = File(ospath.join(self._workdir.name, uid))
        elif isinstance(file, IOBase) or hasattr(file, "read") and not hasattr(file, "open"):
            file0 = file
            path = ospath.join(self._workdir.name, uid)
            file = File(path)
            test_data = file0.read(0)
            if test_data == b"":
                copyfileobj(file0, open(path, "wb"))
            elif test_data == "":
                copyfileobj(file0, open(path, "w"))
            else:
                raise TypeError(f"incorrect read behavior: {file0!r}")
        else:
            file = File(file, open_modes=open_modes)
        item = Item(el_add(self._root, "item", attrib=attrib, namespaces=NAMESPACES), self)
        super().__setitem__(id, item)
        self._href_to_id[href] = id
        self._href_to_file[href] = file
        return item

    def exists(self, href, /):
        return href in self._href_to_id

    @PyLinq.streamify
    def glob(self, pattern="*", dirname="", ignore_case=False):
        pattern = pattern.strip("/")
        if not pattern:
            return
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
                yield self[id]
            except KeyError:
                pass

    @PyLinq.streamify
    def iterdir(self, /, dirname=""):
        dirname = dirname.strip("/")
        for href, id in self._href_to_id.items():
            if posixpath.dirname(href) != dirname:
                continue
            try:
                yield self[id]
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
        assert (href := href.strip("/"))
        if mode not in OPEN_MODES:
            raise ValueError(f"invalid open mode: {mode!r}")
        href_to_file = self._href_to_file
        if href in self._href_to_id:
            if "x" in mode:
                raise FileExistsError(errno.EEXIST, f"file exists: {href!r}")
            file = href_to_file.get(href)
            if file is None:
                href_to_file[href] = file = File(ospath.join(self._workdir.name, str(uuid4())))
            elif not file.check_open_mode(mode):
                path_dst = ospath.join(self._workdir.name, str(uuid4()))
                if "w" not in mode:
                    try:
                        fsrc = file.open("rb", buffering=0)
                    except FileNotFoundError:
                        if "r" in mode:
                            raise
                    else:
                        with fsrc:
                            copyfileobj(fsrc, open(path_dst, "wb"))
                href_to_file[href] = file = File(path_dst)
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

    def read(self, href, /):
        with self.open(href, "rb", buffering=0) as f:
            return f.read()

    read_bytes = read

    def read_text(self, href, /, encoding=None):
        with self.open(href, "r", encoding=encoding) as f:
            return f.read()

    def remove(self, href, /):
        assert (href := href.strip("/"))
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

    def rename(self, href, href_new, /):
        assert (href := href.strip("/"))
        assert (href_new := href_new.strip("/"))
        if href == href_new:
            return
        if href_new in self._href_to_id:
            raise FileExistsError(errno.EEXIST, f"target file exists: {href_new!r}")
        try:
            id = self._href_to_id[href_new] = self._href_to_id.pop(href)
        except LookupError:
            raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
        self[id]["href"] = href_new
        self._href_to_file[href_new] = self._href_to_file.pop(href, None)

    def replace(self, href, dest_href, /):
        assert (href := href.strip("/"))
        assert (dest_href := dest_href.strip("/"))
        if href not in self._href_to_id:
            raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
        if dest_href in self._href_to_id:
            self.remove(dest_href)
        self.rename(href, dest_href)

    @PyLinq.streamify
    def rglob(self, pattern="", dirname="", ignore_case=False):
        pattern = joinpath("**", pattern.lstrip("/"))
        return self.glob(pattern, dirname)

    def stat(self, href, /) -> Optional[stat_result]:
        assert (href := href.strip("/"))
        if href not in self._href_to_id:
            raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
        try:
            stat = self._href_to_file[href].stat
        except LookupError:
            return None
        if stat is None:
            return None
        return stat()

    def touch(self, href, /):
        assert (href := href.strip("/"))
        self.open(href, "ab", buffering=0).close()

    unlink = remove

    def write(self, href, /, data):
        assert (href := href.strip("/"))
        if isinstance(data, File):
            with data.open("rb", buffering=0) as fsrc, self.open("wb", buffering=0) as fdst:
                copyfileobj(fsrc, fdst)
        elif callable(getattr(data, "read", None)):
            test_data = data.read(0)
            if test_data == b"":
                with self.open("wb", buffering=0) as fdst:
                    copyfileobj(data, fdst)
            elif test_data == "":
                with self.open("w") as fdst:
                    copyfileobj(data, fdst)
            else:
                raise TypeError(f"incorrect read behavior: {data!r}")
        elif isinstance(data, (str, PathLike)):
            with open(data, "rb", buffering=0) as fsrc, self.open("wb", buffering=0) as fdst:
                copyfileobj(fsrc, fdst)
        else:
            content = memoryview(data)
            with self.open(href, "wb") as f:
                return f.write(content)

    write_bytes = write

    def write_text(self, href, /, text, encoding=None, errors=None, newline=None):
        assert (href := href.strip("/"))
        with self.open(href, "w", encoding=encoding, errors=errors, newline=newline) as f:
            return f.write(text)


class Spine(dict[str, Itemref]):

    def __init__(self, root: Element, /, manifest: Manifest):
        self._root = root
        self._attrib = root.attrib
        self._proxy = ElementAttribProxy(root)
        self._manifest = manifest
        if len(root):
            has_dangling = False
            for itemref in root.iterfind("*"):
                if itemref.tag != "itemref" and not itemref.tag.endswith("}itemref"):
                    has_dangling = True
                    continue
                idref = itemref.attrib.get("idref")
                if idref is not None and idref in manifest:
                    super().__setitem__(cast(str, idref), Itemref(itemref))
                else:
                    has_dangling = True
            if has_dangling:
                root[:] = (itemref._root for itemref in self.values()) # type: ignore

    def __call__(self, id, /, attrib=None):
        itemref = self.get(id)
        if attrib is None:
            if id in self._manifest:
                return itemref
            elif itemref is not None:
                del self[id]
        elif id in self._manifest:
            if itemref is not None:
                itemref.update(attrib)
            else:
                itemref = self._add(id, attrib)
            return itemref
        elif itemref is not None:
            del self[id]

    def __delitem__(self, key, /):
        pop = self.pop
        if isinstance(key, Item):
            key = key.id
        elif isinstance(key, Itemref):
            key = key.idref
        if isinstance(key, str):
            pop(key, None)
        if isinstance(key, int):
            el = self._root[key]
            pop(el.attrib["id"], None)
        elif isinstance(key, slice):
            for el in self._root[key]:
                pop(el.attrib["id"], None)
        else:
            super().__delitem__(self, key)
        return self

    def __getitem__(self, key, /):
        if isinstance(key, Item):
            key = key.id
        elif isinstance(key, Itemref):
            key = key.idref
        if isinstance(key, int):
            return Itemref(self._root[key])
        elif isinstance(key, slice):
            return list(map(Itemref, self._root[key]))
        else:
            return super().__getitem__(key)

    def __setitem__(self, id, attrib, /):
        if isinstance(id, Item):
            id = id.id
        elif isinstance(id, Itemref):
            id = id.idref
        self[id].update(attrib)
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

    def _add(self, id, /, attrib=None):
        if attrib:
            attrib = dict(attrib, idref=id)
        else:
            attrib = {"idref": id}
        itemref = Itemref(el_add(self._root, "itemref", attrib=attrib, namespaces=NAMESPACES))
        super().__setitem__(id, itemref)
        return itemref

    def add(self, id, /, attrib=None):
        if isinstance(id, Item):
            id = id.id
        if id not in self._manifest:
            raise LookupError(f"no such id in manifest: {id!r}")
        elif id in self:
            raise LookupError(f"id already exists: {id!r}")
        return self._add(id, attrib)

    def clear(self, /):
        self._root.clear()
        super().clear()
        return self

    @PyLinq.streamify
    def iter(self, /):
        for el in self._root.iterfind("{*}itemref"):
            idref = el.attrib.get("idref")
            if idref is None or idref not in self._manifest:
                try:
                    self._root.remove(el)
                    raise RuntimeError(f"removed a dangling itemref element: {el!r}")
                except:
                    pass
            elif idref not in self:
                itemref = self[idref] = Itemref(el)
                yield itemref
            else:
                itemref = self[idref]
                if itemref._root is not el:
                    raise RuntimeError(f"different itemref elements {el!r} and {itemref._root!r} share the same id {idref!r}")
                yield itemref

    def pop(self, id, /, default=undefined):
        if id not in self:
            if default is undefined:
                raise LookupError(f"no such id in manifest: {id!r}")
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
        if id in self:
            return self[id].update(attrib)
        else:
            return self.add(id, attrib)

    def setdefault(self, id, /, attrib=None):
        if id in self:
            return self[id].merge(attrib)
        else:
            return self.add(id, attrib)

    def sort(self, key=id, reverse=False, use_backend_element=False):
        if use_backend_element:
            self._root[:] = sorted(self._root.iterfind("{*}itemref[@idref]"), key=key, reverse=reverse)
        else:
            self._root[:] = (e._root for e in sorted(self.iter(), key=key, reverse=reverse))
        return self

    def merge(self, id_or_attrib=None, /, **attrs):
        if isinstance(id_or_attrib, Item):
            id_or_attrib = id_or_attrib.id
        elif isinstance(id_or_attrib, Itemref):
            id_or_attrib = id_or_attrib.idref
        if isinstance(id_or_attrib, str):
            id = id_or_attrib
            if id in self:
                if attrs:
                    self[id].merge(attrs)
            else:
                self.add(id, attrs)
        else:
            self._proxy.merge(id_or_attrib, **attrs)
        return self

    def update(self, id_or_attrib=None, /, **attrs):
        if isinstance(id_or_attrib, Item):
            id_or_attrib = id_or_attrib.id
        elif isinstance(id_or_attrib, Itemref):
            id_or_attrib = id_or_attrib.idref
        if isinstance(id_or_attrib, str):
            id = id_or_attrib
            if id in self:
                if attrs:
                    self[id].update(attrs)
            else:
                self.add(id, attrs)
        else:
            self._proxy.update(id_or_attrib, **attrs)
        return self


class ePub(ElementProxy):
    __cache_get_key__ = False

    def __init__(self, /, path=None, tempdir=None):
        if path and ospath.lexists(path):
            self._zfile = zfile = ZipFile(path)
            contenter_xml = zfile.read("META-INF/container.xml")
            match = fromstring(contenter_xml).find(
                '{*}rootfiles/{*}rootfile[@media-type="application/oebps-package+xml"][@full-path]', 
            )
            if match is None:
                raise FileNotFoundError(errno.ENOENT, "no opf file specified in container.xml")
            self._opf_path = opf_path = match.attrib["full-path"]
            self._opf_dir, self._opf_name = opf_dir, _ = posixpath.split(opf_path)
            root = fromstring(zfile.read(opf_path))
        else:
            self._opf_path = "OEBPS/content.opf"
            self._opf_dir = "OEBPS"
            self._opf_name = "content.opf"
            root = fromstring(b'''\
<?xml version="1.0" encoding="utf-8"?>
<package version="3.0" unique-identifier="BookId" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="BookId">urn:uuid:%(uuid)s</dc:identifier>
    <dc:language>en</dc:language>
    <dc:title></dc:title>
    <meta property="dcterms:modified">%(mtime)s</meta>
  </metadata>
</package>''' % {
    b"uuid": bytes(str(uuid4()), "utf-8"), 
    b"mtime": bytes(datetime.now().strftime("%FT%XZ"), "utf-8"), 
})
        super().__init__(root)
        self._path = path
        self._tempdir = tempdir
        self.metadata
        self.manifest
        self.spine

    def __del__(self):
        try:
            self._zfile.close()
        except:
            pass

    @property
    def href_to_id(self):
        return self.manifest.href_to_id

    @property
    def href_to_file(self):
        return self.manifest.href_to_file

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
    def version(self, /):
        try:
            return self._attrib["version"]
        except KeyError:
            self._attrib["version"] = "3"
            return "3"

    @property
    def identifier(self, /):
        uid = self.get("unique-identifier")
        text = lambda: f"urn:uuid:{uuid4()}"
        if uid:
            return self.metadata.dc("identifier", find_attrib={"id": uid}, text=text, merge=True, auto_add=True).text
        else:
            return self.metadata.dc("identifier", text=text, merge=True, auto_add=True).text

    @identifier.setter
    def identifier(self, text, /):
        uid = self.get("unique-identifier")
        if uid:
            self.metadata.dc("identifier", find_attrib={"id": uid}, text=text, auto_add=True)
        else:
            self.metadata.dc("identifier", text=text, auto_add=True)

    @property
    def language(self, /):
        return self.metadata.dc("language", text="en", merge=True, auto_add=True).text

    @language.setter
    def language(self, text, /):
        self.metadata.dc("language", text=text, auto_add=True)

    @property
    def title(self, /):
        return self.metadata.dc("title", text="", merge=True, auto_add=True).text

    @title.setter
    def title(self, text, /):
        self.metadata.dc("title", text=text, auto_add=True)

    @property
    def cover(self, /) -> Optional[str]:
        meta = self.metadata.meta(find_attrib={"name": "cover"})
        if meta is None:
            return None
        return meta.get("content")

    @cover.setter
    def cover(self, cover_id, /):
        if isinstance(cover_id, Item):
            cover_id = cover_id.id
        if cover_id not in self.manifest:
            raise LookupError(f"no such item id: {cover_id!r}")
        self.metadata.meta(find_attrib={"name": "cover"}, attrib={"content": cover_id}, auto_add=True)

    @property
    def modified(self, /):
        return self.metadata.meta(
            find_attrib={"property": "dcterms:modified"}, 
            text=lambda: datetime.now().strftime("%FT%XZ"), 
            auto_add=True, 
        ).text

    def pack(
        self, 
        /, 
        path=None, 
        compression=ZIP_DEFLATED, 
        allowZip64=True, 
        compresslevel=None, 
    ):
        if not path and not self._path:
            raise OSError(errno.EINVAL, "please specify a path to save")
        opf_dir, opf_name, opf_path = self._opf_dir, self._opf_name, self._opf_path
        href_to_id = self.href_to_id
        href_to_file = self.href_to_file
        def write_oebps():
            bad_ids = set()
            good_ids = set()
            for href, id in href_to_id.items():
                if href == opf_name:
                    bad_ids.add(id)
                    warn(f"ignore a file, because its href conflicts with OPF: {href!r}")
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
            self.modified
            root = self._root
            if bad_ids:
                root = deepcopy(root)
                manifest = root.find("{*}manifest")
                manifest[:] = (item for item in manifest.iterfind("{*}item[@id]") if item.attrib["id"] in good_ids)
            wfile.writestr(opf_path, tostring(root, encoding="utf-8", xml_declaration=True))
        zfile = self.__dict__.get("_zfile")
        if zfile is None:
            if path is None:
                path = self._path
            with ZipFile(path, "w", compression, allowZip64, compresslevel) as wfile:
                wfile.writestr("mimetype", b"application/epub+zip")
                wfile.writestr("META-INF/container.xml", b'''\
<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
   </rootfiles>
</container>''')
                write_oebps()
        else:
            if path is None or path == self._path:
                raise ValueError(f"not allowed to overwrite the original file: {self._path!r}")
            exclude_files = {
                joinpath(opf_dir, item.attrib["href"])
                for item in fromstring(zfile.read(opf_path)).find("{*}manifest")
            }
            exclude_files.add(opf_path)
            exclude_files.update(joinpath(opf_dir, href) for href in href_to_id)
            with ZipFile(path, "w", compression, allowZip64, compresslevel) as wfile:
                for name, info in zfile.NameToInfo.items():
                    if info.is_dir() or name in exclude_files:
                        continue
                    with zfile.open(name) as fsrc, wfile.open(name, "w") as fdst:
                        copyfileobj(fsrc, fdst)
                write_oebps()

