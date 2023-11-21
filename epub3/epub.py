#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
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
from itertools import permutations, product
from mimetypes import guess_type
from operator import methodcaller
from os import fsdecode, remove, stat, stat_result, PathLike
from pathlib import PurePosixPath
from posixpath import join as joinpath
from pprint import pformat
from re import compile as re_compile, escape as re_escape, Pattern
from shutil import copy, copyfileobj
from tempfile import TemporaryDirectory
from time import mktime
from typing import Any, Callable, Mapping, MutableMapping, Optional
from types import MappingProxyType
from uuid import uuid4
from warnings import warn
from weakref import WeakKeyDictionary, WeakValueDictionary
from zipfile import ZipFile, ZIP_DEFLATED

from .util.helper import items, wrap_open_in_bytes
from .util.proxy import ElementAttribProxy, ElementProxy
from .util.xml import el_add, el_del, el_iterfind, el_set
from .util.undefined import undefined, UndefinedType

try:
    from lxml.etree import fromstring, tostring, _Element as Element, _ElementTree as ElementTree # type: ignore
except ModuleNotFoundError:
    from xml.etree.ElementTree import fromstring, tostring, Element, ElementTree # type: ignore


OPEN_MODES = frozenset(
    "".join(t1) 
    for t0 in product("rwax", ("", "b", "t"), ("", "+")) 
    for t1 in permutations(t0, 3)
)


class FileInEpub:
    __slots__ = ("path", "internal", "open", "stat")

    path: str
    internal: bool
    open: Optional[Callable[..., IOBase]]
    stat: Optional[Callable[[], stat_result]]

    def __init__(
        self, 
        /, 
        path: Optional[str] = None, 
        internal: bool = False, 
        open: Optional[Callable[..., IOBase]] = None, 
        stat: Optional[Callable[[], stat_result]] = None, 
    ):
        if not path:
            if internal:
                raise ValueError("`path` must be specified if `internal` is True")
            elif open is None:
                raise ValueError("`open` must be specified if no `path`")
        else:
            if open is None:
                open = partial(io.open, path)
            if stat is None:
                stat = partial(os.stat, path)
        super().__setattr__("path", path or "")
        super().__setattr__("internal", internal)
        super().__setattr__("open", open)
        super().__setattr__("stat", stat)

    def __fspath__(self, /) -> str:
        return self.path

    def __repr__(self, /) -> str:
        cls = type(self)
        module = cls.__module__
        name = cls.__qualname__
        if module != "__main__":
            name = module + "." + name
        return f"{name}(path={self.path!r}, internal={self.internal!r}, open={self.open!r}, stat={self.stat!r})"

    def __setattr__(self, attr, value, /):
        raise TypeError("can't set property")

    @property
    def name(self, /):
        return posixpath.basename(self.path)


class Item(ElementAttribProxy):
    __const_keys__ = ("id",)
    __protected_keys__ = ("href", "media-type")
    __cache_get_state__ = lambda _, manifest: manifest

    def __init__(self, root, manifest, /):
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
            self._attrib["media-type"] = guess_type(self._attrib["href"])[0] or "application/octet-stream"
        else:
            self._attrib["media-type"] = value

    @property
    def home(self, /):
        return elf._manifest._opf_dir

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

    def update(self, /, attrib=None, merge=False):
        if attrib:
            if not merge:
                if "href" in attrib:
                    href = attrib["href"]
                    self.rename(href)
                    if len(attrib) == 1:
                        return
                    attrib = dict(attrib)
                    del attrib["href"]
            super().update(attrib, merge=merge)

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
        ensure_path=False, 
    ):
        return self._manifest.open(
            self.href, 
            mode=mode, 
            buffering=buffering, 
            encoding=Noencodingne, 
            errors=errors, 
            newline=newline, 
            ensure_path=ensure_path, 
        )

    def read(self, /):
        return self._manifest.read(self.href)

    read_bytes = read

    def read_text(self, /, encoding=None):
        return self._manifest.read(self.href, encoding=encoding)

    def remove(self, /):
        self._manifest.remove(self.href)

    def rename(self, href_new, /):
        self._manifest.rename(self.href, href_new)

    def replace(self, href, /):
        self._manifest.replace(self.href, href)

    def stat(self, /) -> Optional[stat_result]:
        return self._manifest.stat(self.href)

    def touch(self, /):
        self._manifest.touch(self.href)

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
        return f"<{self.tag}>{attrib}\n{pformat(self.list())}"

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


class Manifest(dict):

    def __init__(self, root, opf_dir="", zfile=None):
        self._root = root
        self._attrib = root.attrib
        self._proxy = ElementAttribProxy(root)
        self._opf_dir = opf_dir
        self._zfile = zfile
        self._href_to_id = href_to_id = {}
        self._href_to_file = href_to_file = {}
        if len(root):
            has_dangling = False
            for item in root.iterfind("*"):
                try:
                    id = item.attrib["id"]
                    href = item.attrib["href"]
                except LookupError:
                    has_dangling = True
                    continue
                super().__setitem__(id, Item(item, self))
                href_to_id[href] = id
            if has_dangling:
                root[:] = (item._root for item in self.values())
            if zfile:
                for href in href_to_id:
                    zpath = joinpath(opf_dir, href) if opf_dir else href
                    zinfo = zfile.NameToInfo.get(zpath)
                    if not zinfo or zinfo.is_dir():
                        warn(f"missing file in original epub: {href!r}")
                    else:
                        zmtime = int(mktime((*zinfo.date_time, 0, 0, 0)))
                        href_to_file[href] = FileInEpub( 
                            open=wrap_open_in_bytes(partial(zfile.open, zpath)), 
                            stat=lambda _result=stat_result((
                                0, 0, 0, 0, 0, 0, 
                                zinfo.file_size, 
                                zmtime, 
                                zmtime, 
                                zmtime, 
                            )): _result, 
                        )

    def __del__(self, /):
        try:
            self.__dict__["_workdir"].cleanup()
        except:
            pass

    def __call__(self, href, /):
        try:
            id = self._href_to_id[href]
        except LookupError:
            raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
        return self[id]

    def __delitem__(self, key, /):
        pop = self.pop
        if isinstance(key, int):
            el = self._root[key]
            pop(el.attrib["id"], None)
        elif isinstance(key, slice):
            for el in self._root[key]:
                pop(el.attrib["id"], None)
        elif isinstance(key, str):
            pop(key, None)
        else:
            super().__delitem__(self, key)

    def __getitem__(self, key, /):
        if isinstance(key, int):
            return Item(self._root[key], self)
        elif isinstance(key, slice):
            return [Item(el, self) for el in self._root[key]]
        else:
            return super().__getitem__(key)

    def __setitem__(self, id, value, /):
        if isinstance(value, str):
            if id in self:
                self.rename(self[id]["href"], value)
            else:
                self.add(value, id=id)
        elif isinstance(value, bytes):
            if id not in self:
                raise LookupError(f"no such item id: {id!r}")
            self.write(self[id]["href"], value)
        elif isinstance(value, PathLike):
            if id not in self:
                raise LookupError(f"no such item id: {id!r}")
            href = self[id]["href"]
            self._href_to_file = FileInEpub(fsdecode(value))
        elif isinstance(value, (Mapping, Iterable)):
            if id in self:
                self[id].update(value)
            else:
                attrib = dict(value)
                href = attrib.get("href")
                if not href:
                    raise ValueError("missing href")
                if "media-type" not in attrib:
                    attrib["media-type"] = guess_type(href)[0] or "application/octet-stream"
                self.add(href, id=id, attrib=attrib)
        else:
            raise TypeError("only `bytes`, `str`, `os.PathLike` and `typing.Mapping` are accecptable")

    @cached_property
    def _workdir(self, /):
        return TemporaryDirectory()

    @cached_property
    def href_to_id(self):
        return MappingProxyType(self._href_to_id)

    @cached_property
    def href_to_file(self):
        return MappingProxyType(self._href_to_file)

    @property
    def home(self, /):
        return self._opf_dir

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

    def pop(self, id, default=undefined):
        if id not in self:
            if default is undefined:
                raise LookupError(f"no such item id: {id!r}")
            return default
        item = super().pop(id)
        try:
            self._root.remove(item._root)
        except:
            pass
        href = item["href"]
        self._href_to_id.pop(href, None)
        path = self._href_to_file.pop(href, None)
        if path is not None and path.internal:
            try:
                remove(path.path)
            except:
                pass

    def popitem(self, /):
        id, item = super().popitem()
        try:
            self._root.remove(item._root)
        except:
            pass
        href = item.href
        self._href_to_id.pop(href, None)
        path = self._href_to_file.pop(href, None)
        if path is not None and path.internal:
            try:
                remove(path.path)
            except:
                pass
        return id, item

    def set(self, id, /, href="", attrib=None):
        if id in self:
            if href:
                if attrib:
                    attrib = {**attrib, "href": href}
                else:
                    attrib = {"href": href}
            self[id].update(attrib, merge=False)
        else:
            self.add(href, id=id, attrib=attrib)

    def setdefault(self, id, /, href="", attrib=None):
        if id in self:
            self[id].update(attrib, merge=True)
        else:
            self.add(href, id=id, attrib=attrib)

    def update(self, id, /, attrib=None, merge=False):
        if id not in self:
            raise LookupError(f"no such item id: {id!r}")
        if attrib:
            self[id].update(attrib, merge=merge)

    #################### SubElement Methods #################### 

    def filter(self, /, predicate=None):
        if not callable(predicate):
            return iter(self.values())
        return filter(predicate, self.values())

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
                el.attrib["media-type"] = guess_type(href)[0] or "application/octet-stream"
            if id is None:
                id = str(uuid4())
                self[id] = item = Item(el, self)
                self._href_to_id[href] = id
                self._href_to_file[href] = FileInEpub(ospath.join(self._workdir.name, id), True)
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

    def list(self, /):
        return list(self.iter())

    def sort(self, key=id, reverse=False, use_backend_element=False):
        if use_backend_element:
            self._root[:] = sorted(self._root.iterfind("{*}item[@id][@href]"), key=key, reverse=reverse)
        else:
            self._root[:] = (e._root for e in sorted(self.iter(), key=key, reverse=reverse))

    #################### File System Methods #################### 

    def add(self, href, /, file=None, id=None, media_type=None, stat=None, attrib=None):
        assert (href := href.strip("/"))
        if href in self._href_to_id:
            raise FileExistsError(errno.EEXIST, f"file exists: {href!r}")
        uid = str(uuid4())
        if id is None:
            id = uid
        elif id in self:
            raise LookupError(f"id already exists: {id!r}")
        if media_type is None:
            media_type = guess_type(href)[0] or "application/octet-stream"
        if isinstance(file, (bytes, str, PathLike)):
            path = fsdecode(file)
            if not ospath.isfile(path):
                raise OSError(errno.EINVAL, f"not a file: {path}")
            internal = False
        elif callable(file):
            path = None
            internal = False
        else:
            path = ospath.join(self._workdir.name, uid)
            internal = True
        if internal and hasattr(file, "read"):
            copyfileobj(file, open(path, "wb"))
        if attrib:
            attrib = dict(attrib, id=id, href=href)
        else:
            attrib = {"id": id, "href": href}
        if media_type:
            attrib["media-type"] = media_type
        elif "media-type" not in attrib:
            attrib["media-type"] = guess_type(href)[0] or "application/octet-stream"
        item = Item(el_add(self._root, "item", attrib=attrib, namespaces=NAMESPACES), self)
        self[id] = item
        self._href_to_id[href] = id
        if internal:
            self._href_to_file[href] = FileInEpub(path, True)
        elif path is None:
            self._href_to_file[href] = FileInEpub(open=file, stat=stat)
        else:
            self._href_to_file[href] = FileInEpub(path)
        return item

    def exists(self, href, /):
        return href in self._href_to_id

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
        ensure_path=False, 
    ):
        if mode not in OPEN_MODES:
            raise ValueError(f"invalid open mode: {mode!r}")
        assert (href := href.strip("/"))
        href_to_file = self._href_to_file
        if href in self._href_to_id:
            if "x" in mode:
                raise FileExistsError(errno.EEXIST, f"file exists: {href!r}")
            path = href_to_file.get(href)
            if path is None:
                href_to_file[href] = path = FileInEpub(ospath.join(self._workdir.name, str(uuid4())), True)
            # NOTE: External files are not allowed to be modified. If modifications are necessary, 
            #       they will be copied to the ePub working directory first.
            if ensure_path and not path.path or not path.internal and ("r" not in mode or "+" in mode):
                path_src = path.path
                path_dst = ospath.join(self._workdir.name, str(uuid4()))
                path_new = FileInEpub(path_dst, True)
                if "w" not in mode:
                    if path_src and ospath.isfile(path_src):
                        copy(path_src, path_dst)
                    else:
                        with path.open("rb", buffering=0) as fsrc:
                            copyfileobj(fsrc, open(path_dst, "wb"))
                href_to_file[href] = path = path_new
        elif "r" in mode:
            raise FileNotFoundError(errno.ENOENT, f"no such file: {href!r}")
        else:
            item = self.add(href)
            path = href_to_file[href]
        if "b" not in mode and encoding is None:
            encoding = "utf-8"
        try:
            return path.open(
                mode=mode, 
                buffering=buffering, 
                encoding=encoding, 
                errors=errors, 
                newline=newline, 
            )
        except (FileNotFoundError, LookupError):
            if path.internal:
                open(path, "wb", buffering=0).close()
            return path.open(
                mode=mode, 
                buffering=buffering, 
                encoding=encoding, 
                errors=errors, 
                newline=newline, 
            )

    def read(self, href, /):
        with self.open(href, "rb") as f:
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
        path = self._href_to_file.pop(href, None)
        if path is not None and path.internal:
            try:
                remove(path.path)
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
        if href in self._href_to_id:
            if href not in self._href_to_file:
                self.open(href, "wb", buffering=0).close()
        else:
            self.open(href, "wb", buffering=0).close()

    unlink = remove

    def write(self, href, /, data):
        assert (href := href.strip("/"))
        if isinstance(data, PathLike) or hasattr(data, "read"):
            if isinstance(data, PathLike):
                fsrc = open(data, "rb", buffering=0)
                fsrc_read = fsrc.read
            elif data.read(0) == b"":
                fsrc_read = data.read
            elif isinstance(data, TextIOWrapper):
                fsrc_read = data.buffer.read
            else:
                org_fsrc_read = data.read
                fsrc_read = lambda size: bytes(org_fsrc_read(size), "utf-8")
            bufsize = 1 << 16
            with self.open(href, "wb") as fdst:
                fdst_write = fdst.write
                while (chunk := fsrc_read(bufsize)):
                    fdst_write(chunk)
            return
        if isinstance(data, str):
            content = bytes(data, "utf-8")
        else:
            content = memoryview(data)
        with self.open(href, "wb") as f:
            return f.write(content)

    write_bytes = write

    def write_text(self, href, /, text, encoding=None, errors=None, newline=None):
        assert (href := href.strip("/"))
        with self.open(href, mode="w", encoding=encoding, errors=errors, newline=newline) as f:
            return f.write(text)


class Spine(dict):

    def __init__(self, root, manifest):
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
                if idref in manifest:
                    super().__setitem__(idref, Itemref(itemref))
                else:
                    has_dangling = True
            if has_dangling:
                root[:] = (ref._root for ref in self.values())

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
        if isinstance(key, int):
            el = self._root[key]
            pop(el.attrib["id"], None)
        elif isinstance(key, slice):
            for el in self._root[key]:
                pop(el.attrib["id"], None)
        elif isinstance(key, str):
            pop(key, None)
        else:
            super().__delitem__(self, key)

    def __getitem__(self, key, /):
        if isinstance(key, int):
            return Itemref(self._root[key])
        elif isinstance(key, slice):
            return list(map(Itemref, self._root[key]))
        else:
            return super().__getitem__(key)

    def __setitem__(self, id, attrib, /):
        self[id].update(attrib)

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
        return Itemref(el_add(self._root, "itemref", attrib=attrib, namespaces=NAMESPACES))

    def add(self, id, /, attrib=None):
        if id not in self._manifest:
            raise LookupError(f"no such id in manifest: {id!r}")
        elif id in self:
            raise LookupError(f"id already exists: {id!r}")
        return self._add(id, attrib)

    def clear(self, /):
        self._root.clear()
        super().clear()

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

    def list(self, /):
        return list(self.iter())

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

    def popitem(self, /):
        id, itemref = super().popitem()
        try:
            self._root.remove(itemref._root)
        except:
            pass
        return id, itemref

    def set(self, id, /, attrib=None):
        if id in self:
            self[id].update(attrib, merge=False)
        else:
            self.add(id, attrib)

    def setdefault(self, id, /, attrib=None):
        if id in self:
            self[id].update(attrib, merge=True)
        else:
            self.add(id, attrib)

    def sort(self, key=id, reverse=False, use_backend_element=False):
        if use_backend_element:
            self._root[:] = sorted(self._root.iterfind("{*}itemref[@idref]"), key=key, reverse=reverse)
        else:
            self._root[:] = (e._root for e in sorted(self.iter(), key=key, reverse=reverse))

    def update(self, id, /, attrib=None, merge=False):
        if id not in self:
            raise LookupError(f"no such item id: {id!r}")
        if attrib:
            self[id].update(attrib, merge=merge)


class ePub(ElementProxy):
    __cache_get_key__ = False

    def __init__(self, path=None):
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
        return Manifest(
            el_set(self._root, "{*}manifest", "manifest"), 
            self._opf_dir, 
            self.__dict__.get("_zfile"), 
        )

    @cached_property
    def spine(self, /):
        return Spine(el_set(self._root, "{*}spine", "spine"), self.manifest)

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
        meta = self.metadata.meta('[@name="cover"]')
        if meta is None:
            return None
        return meta.get("content")

    @cover.setter
    def cover(self, cover_id, /):
        if cover_id not in self.manifest:
            raise LookupError(f"no such item id: {cover_id!r}")
        self.metadata.meta('[@name="cover"]', attrib={"content": cover_id}, auto_add=True)

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
                    with wfile.open(joinpath(opf_dir, href), "w") as fdst:
                        copyfileobj(fsrc, fdst)
                    good_ids.add(id)
                finally:
                    fsrc.close()
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


# TODO: 提供一个方法，对于 epub2 的电子书，可以把它的 guide、toc 等元素，等价转换并集中到 nav.xhtml 中
# TODO: 参详一下 ebooklib 的这些内容：
## 1. 各种 EpubItem 的子类
## 2. EpubWriter._write*
## 3. templates, get_template, set_template
## 4. set_direction, direction

