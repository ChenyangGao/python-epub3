#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io>"
__all__ = ["OPEN_MODES", "File", "RootFS", "TemporaryFS"]

import errno
import io
import os
import os.path as ospath
import posixpath
import shutil

from functools import partial, update_wrapper
from inspect import isclass, signature, _ParameterKind
from io import BufferedReader, BufferedWriter, BufferedRandom, TextIOWrapper, DEFAULT_BUFFER_SIZE
from itertools import permutations, product
from os import PathLike
from tempfile import TemporaryDirectory
from typing import Mapping
from uuid import uuid4
from warnings import warn

from .undefined import undefined


OPEN_MODES = frozenset(
    "".join(t1) 
    for t0 in product("rwax", ("", "b", "t"), ("", "+")) 
    for t1 in permutations(t0, 3)
)
CONTAINS_ALL: frozenset = type("ContainsALL", (frozenset,), {
    "__slots__": (), 
    "__and__": staticmethod(lambda _: _), 
    "__bool__": staticmethod(lambda: True), 
    "__contains__": staticmethod(lambda _: True), 
    "__eq__": staticmethod(lambda _: _ is CONTAINS_ALL), 
    "__hash__": staticmethod(lambda: 0), 
    "__or__": staticmethod(lambda _: CONTAINS_ALL), 
    "__repr__": staticmethod(lambda: "CONTAINS_ALL"), 
})()
KEYWORD_ONLY = _ParameterKind.KEYWORD_ONLY
POSITIONAL_OR_KEYWORD = _ParameterKind.POSITIONAL_OR_KEYWORD
VAR_KEYWORD = _ParameterKind.VAR_KEYWORD


def get_any_callable(getter, *keys):
    for key in keys:
        try:
            if callable(fn := getter(key)):
                return fn
        except (LookupError, AttributeError):
            pass


class File:
    __slots__ = ("path", "fs", "open", "open_modes", "_getattr")
    ALL_MODES = frozenset("rwxab+")

    def __init__(
        self, 
        /, 
        path=None, 
        fs=None, 
        open_modes=None, 
    ):
        super().__setattr__("path", path)
        super().__setattr__("fs", fs)
        self._init_open(path, fs, open_modes)

    def __init_subclass__(cls, /, **kwargs):
        raise TypeError("subclassing is not allowed")

    def __repr__(self, /) -> str:
        cls = type(self)
        module = cls.__module__
        name = cls.__qualname__
        if module != "__main__":
            name = module + "." + name
        return "%s(%s)" % (name, ", ".join("%s=%r" % (k, getattr(self, k)) for k in cls.__slots__))

    def __delattr__(self, attr):
        raise TypeError("can't delete any attributes")

    def __getattr__(self, attr, /):
        try:
            return self._getattr(attr)
        except Exception as e:
            raise AttributeError(attr) from e

    def __setattr__(self, attr, value, /):
        raise TypeError("can't set any attributes")

    def _init_open(self, path, fs, open_modes, /):
        cls = type(self)
        code, file_open = cls._get_open(fs)
        use_io_open = file_open is io.open
        if file_open is None:
            code, file_open = cls._get_open(path)
            if file_open is None:
                if not isinstance(path, (bytes, str, PathLike)):
                    raise TypeError("unable to determine how to open the file")
                file_open = partial(io.open, path)
                use_io_open = True
            use_fs = False
        else:
            file_open = partial(file_open, path)
            use_fs = True
        _getattr = None
        if code == 0:
            def _getattr(attr):
                try:
                    return getattr(os, attr)
                except AttributeError:
                    try:
                        return getattr(ospath, attr)
                    except AttributeError:
                        return getattr(shutil, attr)
        elif code == 1:
            _getattr = partial(getattr, fs if use_fs else path)
        elif code == 2:
            _getattr = (fs if use_fs else path).__getitem__
        if _getattr is not None and use_fs:
            _getattr0 = _getattr
            def _getattr(attr, default=undefined, /):
                try:
                    val = _getattr0(attr)
                except (LookupError, AttributeError):
                    if default is undefined:
                        raise
                    return default
                if not callable(val):
                    return val
                if isclass(val) or isinstance(val, staticmethod):
                    return val
                return partial(val, path)
        default_open_modes = _getattr("open_modes", None)
        if default_open_modes is not None:
            open_modes = default_open_modes
        super().__setattr__("_getattr", _getattr)
        open_keywords = cls._open_keywords(file_open)
        if "mode" not in open_keywords or open_modes == "":
            open_modes = frozenset()
        elif open_modes is None:
            open_modes = type(self).ALL_MODES
        elif use_io_open:
            open_modes = frozenset(open_modes) & type(self).ALL_MODES | frozenset("rb")
        else:
            open_modes = frozenset(open_modes) & type(self).ALL_MODES | frozenset("r")
        super().__setattr__("open_modes", open_modes)
        amode = frozenset("rwxa+")
        def open(
            mode="r", 
            buffering=-1, 
            encoding=None, 
            errors=None, 
            newline=None, 
            **kwargs, 
        ):
            if mode not in OPEN_MODES:
                raise ValueError(f"invalid open mode: {mode!r}")
            binary_mode = "b" in mode
            if mode == "r":
                pass
            elif not open_modes:
                if "r" not in mode or "+" in mode:
                    raise ValueError(f"open mode unsupported: {mode!r}")
                mode = "r"
            else:
                if open_modes:
                    if amode & set(mode) - open_modes:
                        raise ValueError(f"open mode unsupported: {mode!r}")
                mode = next(m for m in "rwax" if m in mode) + "+"[:"+" in mode]
            if open_modes:
                if "b" in open_modes:
                    mode += "b"
            if open_keywords is not CONTAINS_ALL:
                kwargs = {k: v for k, v in kwargs.items() if k in open_keywords}
            if open_modes:
                kwargs["mode"] = mode
            if "buffering" in open_keywords:
                kwargs["buffering"] = buffering
                file = file_open(**kwargs)
            else:
                file = file_open(**kwargs)
                if binary_mode and buffering == 0:
                    return file
                bufsize = buffering if buffering > 1 else DEFAULT_BUFFER_SIZE
                if "+" in mode:
                    file = BufferedRandom(file, bufsize)
                elif "r" in mode:
                    file = BufferedReader(file, bufsize)
                else:
                    file = BufferedWriter(file, bufsize)
            if binary_mode:
                return file
            return TextIOWrapper(
                file, 
                encoding=encoding, 
                errors=errors, 
                newline=newline, 
                line_buffering=buffering==1, 
            )
        super().__setattr__("open", open)

    @staticmethod
    def _get_open(f, /):
        if f is None:
            return 0, None
        if callable(open := getattr(f, "open", None)):
            return 1, open
        try:
            if callable(open := f["open"]):
                return 2, open
        except (TypeError, LookupError):
            if callable(f):
                return 3, f
        return -1, None

    @staticmethod
    def _open_keywords(open, /):
        params = signature(open).parameters
        if params:
            names = []
            for name, param in reversed(params.items()):
                if param.kind not in (POSITIONAL_OR_KEYWORD, KEYWORD_ONLY):
                    break
                names.append(name)
            if param.kind is VAR_KEYWORD:
                return CONTAINS_ALL
            return frozenset(names)
        return frozenset()

    def check_open_mode(self, mode="r", /):
        if mode not in OPEN_MODES:
            return False
        if mode == "r":
            return True
        open_modes = self.open_modes
        if not open_modes:
            if "r" not in mode or "+" in mode:
                return False
        else:
            if open_modes and frozenset("rwxa+") & set(mode) - open_modes:
                return False
        return True


class RootFS:

    def __init__(self, root=None, /, joinpath=None):
        none_root = root is None
        if not none_root and callable(open := getattr(root, "open", None)):
            _getattr = partial(getattr, root)
        elif not none_root and callable(open := root["open"]):
            _getattr = root.__getitem__
        elif none_root or isinstance(root, (bytes, str, PathLike)):
            self._fs = None
            if root is None:
                self._root = os.getcwd()
            else:
                self._root = ospath.realpath(root)
                if ospath.isfile(root):
                    raise NotADirectoryError(errno.ENOTDIR, root)
            self._joinpath = ospath.join
            self._open = io.open
            return
        if joinpath is None:
            joinpath = get_any_callable(_getattr, "joinpath", "join") or posixpath.join
        self._fs = root
        self._root = ""
        self._getattr = _getattr
        self._joinpath = joinpath
        self._open = open

    def __repr__(self, /):
        return f"<{type(self).__qualname__}({self._root!r}) at {hex(id(self))}>"

    def _getattr(self, attr, /):
        try:
            return getattr(os, attr)
        except AttributeError:
            try:
                return getattr(ospath, attr)
            except AttributeError:
                return getattr(shutil, attr)

    def __getattr__(self, attr, /):
        try:
            val = self._getattr(attr)
        except (AttributeError, LookupError) as e:
            raise AttributeError(attr) from e
        if not callable(val):
            return val
        if isclass(val) or isinstance(val, staticmethod):
            return val
        def wrapper(name, /, *args, **kwargs):
            return val(self.joinpath(name), *args, **kwargs)
        return update_wrapper(wrapper, val)

    @property
    def name(self, /):
        return self._root

    @property
    def root(self, /):
        return self._root

    def joinpath(self, /, *paths):
        return self._joinpath(self._root, *paths)

    def open(
        self, 
        name, 
        /, 
        mode='r', 
        buffering=-1, 
        encoding=None, 
        errors=None, 
        newline=None, 
    ):
        return self._open(
            self.joinpath(name), 
            mode=mode, 
            buffering=buffering, 
            encoding=encoding, 
            errors=errors, 
            newline=newline, 
        )


class TemporaryFS(RootFS):

    def __init__(self, root=None, /, joinpath=None):
        none_root = root is None
        if not none_root and callable(open := getattr(root, "open", None)):
            _getattr = partial(getattr, root)
        elif not none_root and callable(open := root["open"]):
            _getattr = root.__getitem__
        elif none_root or isinstance(root, (bytes, str, PathLike)):
            self._fs = None
            temdir = TemporaryDirectory(dir=root)
            self._root = temdir.name
            self._joinpath = ospath.join
            self._open = io.open
            self._cleanup = temdir.cleanup
            return
        else:
            raise TypeError(f"can't get `open` method from: {fs!r}")
        if joinpath is None:
            joinpath = get_any_callable(_getattr, "joinpath", "join") or posixpath.join
        self._fs = root
        self._root = root = ""
        self._getattr = _getattr
        self._joinpath = joinpath
        self.open = open
        remove = get_any_callable(_getattr, "remove", "rm")
        if remove is None:
            warn(f"can't get `remove` and `rm` methods from: {fs!r}")
            self.remove = lambda *args, **kwargs: None
            self._cleanup = lambda: None
            return
        self.remove = remove
        mkdir = get_any_callable(_getattr, "mkdir", "makedir")
        if mkdir is not None:
            name = str(uuid4())
            try:
                mkdir(name)
            except:
                warn(f"can't make temporary directory: {name!r} on {fs!r}")
            else:
                self._root = root = name
        if root:
            rmtree = get_any_callable(_getattr, "rmtree", "removetree")
            if rmtree is not None:
                def _open(path, *args, **kwargs):
                    return open(joinpath(root, path), *args, **kwargs)
                self.open = update_wrapper(_open, open)
                def _remove(path):
                    remove(joinpath(root, path))
                self.remove = update_wrapper(_remove, remove)
                self._cleanup = lambda: rmtree(root)
                return
        created = set()
        def _open(path, mode="r", **kwargs):
            path = joinpath(root, path)
            file = open(path, mode=mode, **kwargs)
            if "r" not in mode:
                created.add(path)
            return file
        self.open = update_wrapper(_open, open)
        def _remove(path):
            path = joinpath(root, path)
            remove(path)
            created.discard(path)
        self.remove = update_wrapper(_remove, remove)
        rmdir = get_any_callable(_getattr, "rmdir", "removedir")
        def _cleanup():
            for path in tuple(created):
                try:
                    remove(path)
                except:
                    pass
            if root and rmdir is not None:
                try:
                    rmdir(root)
                except:
                    pass
        self._cleanup = _cleanup

    def __repr__(self, /):
        return f"<{type(self).__qualname__}({self._fs!r}) {self._root!r} at {hex(id(self))}>"

    def __del__(self, /):
        self.cleanup()

    def __enter__(self, /):
        return self

    def __exit__(self, exc, value, tb, /):
        self.cleanup()

    def cleanup(self, /):
        try:
            self._cleanup()
        except:
            pass

