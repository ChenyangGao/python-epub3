#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io>"
__all__ = ["UndefinedType", "undefined"]


class UndefinedType:
    __slots__ = ()

    def __new__(cls, /):
        try:
            return cls.__instance__
        except AttributeError:
            instance = cls.__instance__ = super().__new__(cls)
            return instance

    def __init_subclass__(cls, /, **kwargs):
        raise TypeError("subclassing is not allowed")

    def __eq__(self, other, /):
        return self is other

    __bool__ = staticmethod(lambda: False)
    __hash__ = staticmethod(lambda: 0) # type: ignore
    __repr__ = staticmethod(lambda: "undefined") # type: ignore


undefined = UndefinedType()

