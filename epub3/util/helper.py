#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__all__ = ["get", "items", "posix_glob_translate_iter", "wrap_open_in_bytes"]

from fnmatch import translate as wildcard_translate
from io import BufferedReader, BufferedWriter, BufferedRandom, TextIOWrapper, DEFAULT_BUFFER_SIZE
from re import compile as re_compile
from typing import ItemsView, Iterator, Optional, Mapping


def get(m, /, key, default=None):
    try:
        return m.get(key, default)
    except AttributeError:
        try:
            return m[key]
        except LookupError:
            return default


def items(m, /):
    if isinstance(m, Mapping):
        try:
            m = m.items()
        except Exception:
            m = ItemsView(m)
    return m


def posix_glob_translate_iter(pattern: str) -> Iterator[str]:
    for part in pattern.split("/"):
        if not part:
            continue
        if part == "*":
            yield "[^/]*"
        elif len(part) >=2 and not part.strip("*"):
            yield "[^/]*(?:/[^/]*)*"
        else:
            yield wildcard_translate(part)[4:-3].replace(".*", "[^/]*")


def wrap_open_in_bytes(open_in_bytes, /):
    def open(
        mode="r", 
        buffering=-1, 
        encoding=None, 
        errors=None, 
        newline=None, 
    ):
        for mode0 in ("r", "w", "a", "x"):
            if mode0 in mode:
                break
        else:
            raise ValueError(f"invalid open mode: {mode!r}")
        file = open_in_bytes(mode0 + "+"[:"+" in mode])
        if "b" in mode and buffering == 0:
            return file
        bufsize = buffering if buffering > 1 else DEFAULT_BUFFER_SIZE
        if "+" in mode:
            file = BufferedRandom(file, bufsize)
        elif "r" in mode0:
            file = BufferedReader(file, bufsize)
        else:
            file = BufferedWriter(file, bufsize)
        if "b" in mode:
            return file
        return TextIOWrapper(
            file, 
            encoding=encoding, 
            errors=errors, 
            newline=newline, 
            line_buffering=buffering==1, 
        )
    return open

