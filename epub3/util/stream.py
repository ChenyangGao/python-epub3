#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = [
    "typed_method", "Stream", "ItertoolsMixin", "AggregateMixin", "PyLinq", 
]

import itertools

from collections import deque
from functools import reduce, update_wrapper
from operator import attrgetter
from typing import Iterable, Mapping, Sequence, Set

from .undefined import undefined


identity_function = lambda x: x


def typed_method(f):
    def wrapper(self, *args, **kwargs):
        obj = type(self)(f(self, *args, **kwargs))
        if hasattr(obj, '__initialize__'):
            obj.__initialize__(self)
        return obj
    return update_wrapper(wrapper, f)


def iterable(obj):
    'Return whether the object is iterable'
    try:
        iter(obj)
        return True
    except TypeError:
        return False


class Stream(Iterable):

    __slots__ = ("iterable",)

    def __init__(self, iterable):
        super().__setattr__("iterable", iterable)

    def __repr__(self, /) -> str:
        cls = type(self)
        module = cls.__module__
        name = cls.__qualname__
        if module != "__main__":
            name = module + "." + name
        return "%s(%r)" % (name, self.iterable)

    def __contains__(self, element):
        return element in self.iterable

    def __delattr__(self, attr):
        raise TypeError("can't delete any attributes")

    def __getattr__(self, attr):
        return getattr(self.iterable, attr)

    def __getitem__(self, n):
        return self.iterable[n]

    def __iter__(self):
        return iter(self.iterable)

    def __len__(self):
        return len(self.iterable)

    def __matmul__(self, other):
        return type(self)(other)

    def __next__(self):
        return next(self.iterable)

    def __rmatmul__(self, other):
        return type(self)(other)

    def __setattr__(self, attr, val):
        raise TypeError("can't set any attributes")

    @property
    def each(self):
        return Eacher(self)

    @classmethod
    def streamify(cls, func, /):
        def wrapper(*args, **kwargs):
            r = func(*args, **kwargs)
            if iterable(r):
                return cls(r)
            return r
        return update_wrapper(wrapper, func)

    def collect(self, func=None, *args, **kwargs):
        if func is None:
            return list(self)
        r = func(self, *args, **kwargs)
        return self @ r if iterable(r) else r

    def convert(self, transform=None):
        if transform is None:
            return self.iterable
        return transform(self)

    def filter(self, func=None):
        return self @ filter(func, self)

    def list(self):
        return list(self)

    def map(self, func=None):
        if func is None:
            return self
        return self @ map(func, self)

    def reduce(self, func):
        return reduce(func, self)

    def transform(self, transform=None):
        if transform is not None:
            super().__setattr__("iterable", transform(self))
        return self


class Eacher(Stream):

    __slots__ = ("iterable",)

    def __getattr__(self, attr):
        return self.map(attrgetter(attr))

    def __call__(self, *args, **kwds):
        return self.map(lambda x: x(*args, **kwds))


class ItertoolsMixin:

    accumulate = typed_method(itertools.accumulate)

    try:
        batched = typed_method(itertools.batched) # type: ignore
    except AttributeError:
        @typed_method
        def batched(self, n=1):
            if n < 1:
                raise ValueError('n must be at least one')
            it = iter(self.iterable)
            while batch := tuple(islice(it, n)):
                yield batch

    chain = typed_method(itertools.chain)

    def chain_from_iterable(self, iterables):
        return self.chain(itertools.chain.from_iterable(iterables))

    combinations = typed_method(itertools.combinations)
    combinations_with_replacement = typed_method(itertools.combinations_with_replacement)
    compress = typed_method(itertools.compress)
    cycle = typed_method(itertools.cycle)

    @typed_method
    def dropwhile(self, predicate=bool):
        return itertools.dropwhile(predicate, self.iterable)

    @typed_method
    def filterfalse(self, predicate=bool):
        return itertools.filterfalse(predicate, self.iterable)

    groupby = typed_method(itertools.groupby)
    islice = typed_method(itertools.islice)
    pairwise = typed_method(itertools.pairwise)
    permutations = typed_method(itertools.permutations)
    product = typed_method(itertools.product)

    @typed_method
    def starmap(self, func):
        return itertools.starmap(func, self.iterable)

    @typed_method
    def takewhile(self, predicate):
        return itertools.takewhile(predicate, self.iterable)

    tee = typed_method(itertools.tee)
    zip_longest = typed_method(itertools.zip_longest)


class AggregateMixin:

    def aggregateif(self, predicate=None, aggfunc=sum, *args, **kwds):
        return aggfunc(filter(predicate, self), *args, **kwds)

    def aggregatemap(self, mapfunc=None, aggfunc=sum, *args, **kwds):
        if mapfunc is not None:
            self = map(mapfunc, self)
        return aggfunc(self, *args, **kwds)

    def all(self, predicate=None):
        return all(filter(predicate, self))

    def any(self, predicate=None):
        return any(filter(predicate, self))

    def max(self, default=undefined, key=None):
        kwargs = {}
        if default is not undefined:
            kwargs['default'] = default
        if key is not None:
            kwargs['key'] = key
        return max(self, **kwargs)

    def min(self, default=undefined, key=None):
        kwargs = {}
        if default is not undefined:
            kwargs['default'] = default
        if key is not None:
            kwargs['key'] = key
        return min(self, **kwargs)

    def sum(self, start=0):
        return sum(self, start)

    def count(self):
        try:
            return len(self)
        except TypeError:
            return sum(1 for i in self)

    def average(self, default=undefined):
        try:
            n, total = len(self), sum(self)
        except TypeError:
            n, total = 0, 0
            for n, d in enumerate(self, 1):
                total += d
        if n:
            return total / n
        elif default is not undefined:
            return default
        raise LookupError('No elements exception occured')

    def median(self, default=undefined, key=None):
        result = sorted(self, key=key)
        length = len(result)
        if length:
            q, r = divmod(length, 2)
            return result[q] if r else (result[q-1] + result[q]) / 2
        elif default is not undefined:
            return default
        raise LookupError('No elements exception occured')

    def quantify(self, pred=bool):
        "Given a predicate that returns True or False, count the True results."
        return self.map(pred).sum()


class PyLinq(Stream, AggregateMixin, ItertoolsMixin):

    def __init__(self, iterable=None):
        if iterable is None:
            iterable = []
        super().__init__(iterable)

    def iter(self):
        return self @ iter(self.iterable)

    def reversed(self):
        return self @ reversed(self.iterable)

    def length(self):
        return self @ len(self.iterable)

    def add(self, element):
        return self.chain((element,))

    def all_equal(self):
        "Returns True if all the elements are equal to each other"
        g = iter(self.groupby())
        return next(g, True) and not next(g, False)

    def contains(self, element, key=None):
        return element in self.map(key)

    def difference(self, other, key=None, left_key=None, right_key=None):
        other = (self @ other).map(key or right_key)
        selectors = self.map(key or left_key).notin(other)
        return self.compress(selectors)

    @typed_method
    def distinct(self, key=None):
        # A simpler but not equivalent implementation as following:
        # return self @ self.group_by(key).each.first()
        hashable, unhashable = set(), []
        for i, k in self.pair(key):
            if k not in hashable and k not in unhashable:
                try:
                    hashable.add(k)
                except TypeError:
                    unhashable.append(k)
                yield i

    def element_at(self, n, default=undefined):
        try:
            return self[n]
        except TypeError as exc:
            if type(n) is int:
                if n >= 0:
                    r = tuple(self.islice(n, n+1))
                    if r:
                        return r[0]
                else:
                    r = deque(self, -n)
                    if len(r) == -n:
                        return r[0]
            if default is not undefined:
                return default
            raise LookupError(f'No element found at {n!r}') from exc

    def first(self, default=undefined):
        # self.element_at(0, default)
        if default is undefined:
            try:
                return next(iter(self))
            except StopIteration as exc:
                raise LookupError('No such first element') from exc
        return next(iter(self), default)

    def first_true(self, default=None, predicate=None):
        """Returns the first true value in the iterable.

        If no true value is found, returns *default*

        If *predicate* is not None, returns the first item
        for which predicate(item) is true.

        """
        return next(iter(self.filter(predicate)), default)

    @typed_method
    def flatten(list_of_lists):
        "Flatten one level of nesting"
        return itertools.chain.from_iterable(self.iterable)

    def group_by(self, key=None):
        groupers = self.orderby(key=key).groupby(key=key)
        return groupers.map(lambda args: Grouper.make_grouper(*args))

    @typed_method
    def group_join(self, other, key=None, left_key=None, right_key=None):
        left_key, right_key = key or left_key, key or right_key
        left = {i.key: tuple(i) for i in self.group_by(left_key)}
        right = {i.key: tuple(i) for i in (self @ other).group_by(right_key)}
        for k in sorted(left.keys() | right.keys()):
            grouper = itertools.product(left.get(k, ()), right.get(k, ()))
            yield Grouper.make_grouper(k, grouper)

    def intersection(self, other, key=None, left_key=None, right_key=None):
        return self.join(other, key, left_key, right_key).map(lambda x: x[0])

    def isin(self, other):
        if isinstance(other, Stream):
            other = other.data
        if not isinstance(other, (Set, Mapping)):
            if not isinstance(other, Sequence):
                other = tuple(other)
            try:
                other = set(other)
            except TypeError:
                pass
        return self.map(lambda x: x in other)

    def join(self, other, key=None, left_key=None, right_key=None):
        left_key = key or left_key or identity_function
        right_key = key or right_key or identity_function
        judge = lambda x: left_key(x[0]) == right_key(x[1])
        return self.product(other).filter(judge)

    def last(self, default=undefined):
        # self.element_at(-1, default)
        value = default
        for value in self: pass
        if value is undefined:
            raise LookupError('No such last element')
        return value

    @typed_method
    def ncycles(self, n):
        "Returns the sequence elements n times"
        return itertools.chain.from_iterable(itertools.repeat(tuple(self.iterable), n))

    def nth(self, n, default=undefined):
        "Returns the nth item or a default value"
        if isinstance(self.iterable, Sequence):
            try:
                return self.iterable[n]
            except LookupError:
                if default is undefined:
                    raise
                return default
        try:
            return next(iter(self.islice(n, None)))
        except StopIteration as e:
            if default is undefined:
                raise LookupError(n) from e
            return default

    @typed_method
    def prepend(self, *values):
        "Prepend a single value in front of an iterator"
        return itertools.chain(values, self.iterable)

    def take(self, n):
        return self.islice(n)

    def notin(self, other):
        return self.isin(other).map(lambda x: not x)

    def orderby(self, key=None, reverse=False):
        return self.collect(sorted, key=key, reverse=reverse)

    def order_by(self, kwargs_orders=None, reverse_orders=False):
        data = list(self)
        if kwargs_orders:
            if reverse_orders:
                kwargs_orders = reversed(kwargs_orders)
            for kwargs in kwargs_orders:
                data.sort(**kwargs)
        return self @ data

    @typed_method
    def pair(self, key=None):
        if key is None:
            for i in self:
                yield i, i
        else:
            for i in self:
                yield i, key(i)

    def select(self, selector=None):
        return self.map(selector)

    def select_many(self, selector=None):
        return self.map(selector).chain_self_iterable()

    def single(self, default=undefined):
        n = 0
        for n, v in zip(range(1, 3), self): pass
        if n == 0:
            if default is not undefined:
                return default
            raise LookupError('No elements exception occured')
        elif n == 2:
            raise LookupError('More than one element exception occured')
        return v

    def skip(self, n):
        return self.islice(n, None)

    def skipwhile(self, predicate):
        return self.dropwhile(predicate)

    def tail(self, n):
        return self.collect(deque, n)

    def where(self, predicate=None):
        return self.filter(predicate)

    def zip(self, *iterables):
        return zip(self, *iterables)


class Grouper(PyLinq):
    __slots__ = ("iterable", "key")

    def __initialize__(self, obj):
        object.__setattr__(self, "key", obj.key)

    def __matmul__(self, other):
        return self.make_grouper(other, self.key)

    @classmethod
    def make_grouper(cls, key, data):
        self = cls(data)
        self.key = key
        return self

