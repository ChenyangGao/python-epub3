#!/usr/bin/env python
# coding: utf-8

__all__: list[str] = []

import warnings

warnings.formatwarning = lambda message, category, filename, lineno, line=None: \
    f"{filename}:{lineno}: {category.__qualname__}: {message}\n"

from . import _init_mimetypes




