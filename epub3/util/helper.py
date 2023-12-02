#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io>"
__all__ = ["get", "guess_media_type", "keys", "values", "items", "posix_glob_translate_iter", "sup"]

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


def sup(exists, x=1):
    """Find the smallest available integer greater than or equal to `x`.

    :param exists: Determine if the value exists (unavailable), return True if it does.
    :param x: Start value.

    :return: The smallest integer greater than or equal to the initial value 
             x for which calling exists returns False.
    """
    δ = 1
    while exists(x):
        x += δ
        δ <<= 1
    if δ <= 2:
        return x
    δ >>= 2
    x -= δ
    while δ > 1:
        δ >>= 1
        if exists(x):
            x += δ
        else:
            x -= δ
    return x + exists(x)

