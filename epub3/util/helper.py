#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io>"
__all__ = ["get", "guess_media_type", "keys", "values", "items", "posix_glob_translate_iter"]

from fnmatch import translate as wildcard_translate
from mimetypes import guess_type
from typing import ItemsView, Iterator, KeysView, Mapping, ValuesView


def get(m, /, key, default=None):
    try:
        return m.get(key, default)
    except AttributeError:
        try:
            return m[key]
        except LookupError:
            return default


def guess_media_type(name: str, /, default: str = "application/octet-stream") -> str:
    return guess_type(name)[0] or default


def keys(m, /):
    if isinstance(m, Mapping):
        try:
            return m.keys()
        except Exception:
            return KeysView(m)
    return m


def values(m, /):
    if isinstance(m, Mapping):
        try:
            return m.values()
        except Exception:
            return ValuesView(m)
    return m


def items(m, /):
    if isinstance(m, Mapping):
        try:
            return m.items()
        except Exception:
            return ItemsView(m)
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

