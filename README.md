# python-epub3

## An awsome epub3 library.

[python-epub3](https://github.com/ChenyangGao/python-epub3) is a Python library for managing ePub 3 books.

**WARNING** Currently under development, please do not use in production environment.

## Installation

Install through [github](https://github.com/ChenyangGao/python-epub3):

```console
pip install git+https://github.com/ChenyangGao/python-epub3
```

Install through [pypi](https://pypi.org/project/python-epub3/):

```console
pip install python-epub3
```

## Quickstart

```python
>>> # Import the `python-epub3` module
>>> from epub3 import ePub
>>> # Create an e-book, which can accept an actual existing e-book path
>>> book = ePub()
>>> book
<{http://www.idpf.org/2007/opf}package>{'version': '3.0', 'unique-identifier': 'BookId'}
>>> # View metadata
>>> book.metadata
<{http://www.idpf.org/2007/opf}metadata>
[<{http://purl.org/dc/elements/1.1/}identifier>{'id': 'BookId'} text='urn:uuid:d6cc8f4a-d489-47c9-8b69-97dd597e02c3',
 <{http://purl.org/dc/elements/1.1/}language> text='en',
 <{http://purl.org/dc/elements/1.1/}title>,
 <{http://www.idpf.org/2007/opf}meta>{'property': 'dcterms:modified'} text='2023-11-21T16:55:42Z']
>>> # Modify title, i.e. dc:title
>>> book.title = "my book"
>>> # Modify language, i.e. dc:language
>>> book.language = "zh-CN"
>>> # Update modification time
>>> book.modified
'2023-11-21T16:56:23Z'
>>> # View metadata again
>>> book.metadata
<{http://www.idpf.org/2007/opf}metadata>
[<{http://purl.org/dc/elements/1.1/}identifier>{'id': 'BookId'} text='urn:uuid:d6cc8f4a-d489-47c9-8b69-97dd597e02c3',
 <{http://purl.org/dc/elements/1.1/}language> text='zh-CN',
 <{http://purl.org/dc/elements/1.1/}title> text='my book',
 <{http://www.idpf.org/2007/opf}meta>{'property': 'dcterms:modified'} text='2023-11-21T16:56:23Z']
>>> # Add a href
>>> item = book.manifest.add("index.xhtml")
>>> item
<Item({'id': '6053413d-b534-4409-9e9f-7a5cf0a74da9', 'href': 'index.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1066e75d0>
>>> # Add the above file to spine
>>> book.spine.add(item.id)
<Itemref({}) at 0x1076de2d0>
>>> # Open the above file and write some textual data
>>> file = item.open("w")
>>> file.write('''<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html>
... <html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
... <head>
...   <title></title>
... </head>
... <body>
...   <p>&#160;</p>
... </body>
... </html>''')
211
>>> file.close()
>>> # Add a href and associate it with an external path
>>> item = book.manifest.add("cover.png", "/path/to/cover.png")
>>> item
<Item({'id': '35f19873-121d-42f9-9d56-e99cdac7d885', 'href': 'cover.png', 'media-type': 'image/png'}) at 0x1066f5850>
>>> # Set cover
>>> book.cover = item.id
>>> book.cover
'35f19873-121d-42f9-9d56-e99cdac7d885'
>>> # Get <meta> metadata item through function
>>> book.metadata.meta('[@name="cover"]')
<{http://www.idpf.org/2007/opf}meta>{'name': 'cover', 'content': '35f19873-121d-42f9-9d56-e99cdac7d885'}
>>> # Get <dc:name> metadata item through function
>>> book.metadata.dc("title")
<{http://purl.org/dc/elements/1.1/}title> text='my book'
>>> # Pack and save the book
>>> book.pack("book.epub")
```

## Features

...

## Documentation

[https://python-epub3.readthedocs.io](https://python-epub3.readthedocs.io)
