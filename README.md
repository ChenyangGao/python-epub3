# python-epub3

## An awsome epub3 library.

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/python-epub3)
![PyPI - Version](https://img.shields.io/pypi/v/python-epub3)
![PyPI - Downloads](https://img.shields.io/pypi/dm/python-epub3)
![PyPI - Format](https://img.shields.io/pypi/format/python-epub3)
![PyPI - Status](https://img.shields.io/pypi/status/python-epub3)

![GitHub](https://img.shields.io/github/license/ChenyangGao/python-epub3)
![GitHub all releases](https://img.shields.io/github/downloads/ChenyangGao/python-epub3/total)
![GitHub language count](https://img.shields.io/github/languages/count/ChenyangGao/python-epub3)
![GitHub issues](https://img.shields.io/github/issues/ChenyangGao/python-epub3)
![Codecov](https://img.shields.io/codecov/c/github/ChenyangGao/python-epub3)

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

Let's say there is a `sample.epub`, with the `content.opf` file content is

```xml
<?xml version="1.0" encoding="UTF-8"?>
<package version="3.3" unique-identifier="pub-id" xmlns="http://www.idpf.org/2007/opf" >
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
       <dc:identifier id="pub-id">urn:uuid:bb4d4afe-f787-4d21-97b8-68f6774ba342</dc:identifier>
       <dc:title>ePub</dc:title>
       <dc:language>en</dc:language>
       <meta property="dcterms:modified">2989-06-04T00:00:00Z</meta>
    </metadata>
   <manifest>
      <item
          id="nav"
          href="nav.xhtml"
          properties="nav"
          media-type="application/xhtml+xml"/>
      <item
          id="intro"
          href="intro.xhtml"
          media-type="application/xhtml+xml"/>
      <item
          id="c1"
          href="chap1.xhtml"
          media-type="application/xhtml+xml"/>
      <item
          id="c1-answerkey"
          href="chap1-answerkey.xhtml"
          media-type="application/xhtml+xml"/>
      <item
          id="c2"
          href="chap2.xhtml"
          media-type="application/xhtml+xml"/>
      <item
          id="c2-answerkey"
          href="chap2-answerkey.xhtml"
          media-type="application/xhtml+xml"/>
      <item
          id="c3"
          href="chap3.xhtml"
          media-type="application/xhtml+xml"/>
      <item
          id="c3-answerkey"
          href="chap3-answerkey.xhtml"
          media-type="application/xhtml+xml"/>
      <item
          id="notes"
          href="notes.xhtml"
          media-type="application/xhtml+xml"/>
      <item
          id="cover"
          href="images/cover.svg"
          properties="cover-image"
          media-type="image/svg+xml"/>
      <item
          id="f1"
          href="images/fig1.jpg"
          media-type="image/jpeg"/>
      <item
          id="f2"
          href="images/fig2.jpg"
          media-type="image/jpeg"/>
      <item
          id="css"
          href="style/book.css"
          media-type="text/css"/>
   </manifest>
    <spine
        page-progression-direction="ltr">
    <itemref
        idref="intro"/>
    <itemref
        idref="c1"/>
    <itemref
        idref="c1-answerkey"
        linear="no"/>
    <itemref
        idref="c2"/>
    <itemref
        idref="c2-answerkey"
        linear="no"/>
    <itemref
        idref="c3"/>
    <itemref
        idref="c3-answerkey"
        linear="no"/>
    <itemref
        idref="notes"
        linear="no"/>
    </spine>
</package>
```

Import the `python-epub3` module

```python
>>> from epub3 import ePub
```

Create an e-book, which can take an actual existing e-book path as argument

```python
>>> book = ePub("sample.epub")
>>> book
<ePub(<{http://www.idpf.org/2007/opf}package>, attrib={'version': '3.0', 'unique-identifier': 'BookId'}) at 0x102a93810>
```

View metadata

```python
>>> book.metadata
<Metadata(<{http://www.idpf.org/2007/opf}metadata>) at 0x1035c3c50>
[<DCTerm(<{http://purl.org/dc/elements/1.1/}identifier>, attrib={'id': 'BookId'}, text='urn:uuid:bb4d4afe-f787-4d21-97b8-68f6774ba342') at 0x1031ea6d0>,
 <DCTerm(<{http://purl.org/dc/elements/1.1/}language>, text='en') at 0x1035e4710>,
 <DCTerm(<{http://purl.org/dc/elements/1.1/}title>, text='ePub') at 0x1035a00d0>,
 <Meta(<{http://www.idpf.org/2007/opf}meta>, attrib={'property': 'dcterms:modified'}, text='2989-06-04T00:00:00Z') at 0x1035a0850>]
```

View the identifier, i.e. `dc:identifier`

```python
>>> identifier = book.identifier
>>> identifier
'urn:uuid:bb4d4afe-f787-4d21-97b8-68f6774ba342'
>>> isinstance(identifier, str)
True
```

View and modify the title, i.e. `dc:title`

```python
>>> title = book.title
>>> title
'ePub'
>>> book.title = "my first book"
>>> title
'my first book'
```

View and modify the language, i.e. `dc:language`

```python
>>> language = book.language
>>> language
'en'
>>> book.language = "en-US"
>>> language
'en-US'
```

View and update the modification time 😂

```python
>>> book.modified
'2989-06-04T00:00:00Z'
>>> e.mark_modified()
'3000-01-01T00:00:00Z'
```

View metadata again

```python
>>> book.metadata
<Metadata(<{http://www.idpf.org/2007/opf}metadata>) at 0x1075cdfd0>
[<DCTerm(<{http://purl.org/dc/elements/1.1/}identifier>, attrib={'id': 'BookId'}, text='urn:uuid:bb4d4afe-f787-4d21-97b8-68f6774ba342') at 0x10750c350>,
 <DCTerm(<{http://purl.org/dc/elements/1.1/}language>, text='en') at 0x10a6835d0>,
 <DCTerm(<{http://purl.org/dc/elements/1.1/}title>, text='ePub') at 0x10a682550>,
 <Meta(<{http://www.idpf.org/2007/opf}meta>, attrib={'property': 'dcterms:modified'}, text='3000-01-01T00:00:00Z') at 0x10a77f6d0>]
```

View manifest

```python
>>> book.manifest
{'nav': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x1073e1e10>,
 'intro': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'intro', 'href': 'intro.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1073e2190>,
 'c1': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c1', 'href': 'chap1.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1073e25d0>,
 'c1-answerkey': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c1-answerkey', 'href': 'chap1-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1073e2990>,
 'c2': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c2', 'href': 'chap2.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1073e3350>,
 'c2-answerkey': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c2-answerkey', 'href': 'chap2-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1075aded0>,
 'c3': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c3', 'href': 'chap3.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1075af950>,
 'c3-answerkey': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c3-answerkey', 'href': 'chap3-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1075ae710>,
 'notes': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'notes', 'href': 'notes.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1075ae3d0>,
 'cover': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'cover', 'href': 'images/cover.svg', 'properties': 'cover-image', 'media-type': 'image/svg+xml'}) at 0x1075ae610>,
 'f1': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f1', 'href': 'images/fig1.jpg', 'media-type': 'image/jpeg'}) at 0x109a39950>,
 'f2': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f2', 'href': 'images/fig2.jpg', 'media-type': 'image/jpeg'}) at 0x107534310>,
 'css': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'css', 'href': 'style/book.css', 'media-type': 'text/css'}) at 0x107534290>}

>>> book.manifest.list()
[<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x1073e1e10>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'intro', 'href': 'intro.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1073e2190>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c1', 'href': 'chap1.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1073e25d0>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c1-answerkey', 'href': 'chap1-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1073e2990>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c2', 'href': 'chap2.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1073e3350>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c2-answerkey', 'href': 'chap2-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1075aded0>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c3', 'href': 'chap3.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1075af950>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c3-answerkey', 'href': 'chap3-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1075ae710>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'notes', 'href': 'notes.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1075ae3d0>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'cover', 'href': 'images/cover.svg', 'properties': 'cover-image', 'media-type': 'image/svg+xml'}) at 0x1075ae610>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f1', 'href': 'images/fig1.jpg', 'media-type': 'image/jpeg'}) at 0x109a39950>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f2', 'href': 'images/fig2.jpg', 'media-type': 'image/jpeg'}) at 0x107534310>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'css', 'href': 'style/book.css', 'media-type': 'text/css'}) at 0x107534290>]
```

Get an item

```python
>>> book.manifest[0]
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x1073e1e10>

>>>book.manifest['nav'] 
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x1073e1e10>

>>> book.manifest('nav.xhtml')
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x1073e1e10>
```

View spine

```python
>>> book.spine
{'intro': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'intro'}) at 0x107533c90>,
 'c1': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c1'}) at 0x109a88ed0>,
 'c1-answerkey': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c1-answerkey'}) at 0x109a88f50>,
 'c2': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c2'}) at 0x109a89110>,
 'c2-answerkey': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c2-answerkey'}) at 0x109a891d0>,
 'c3': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c3'}) at 0x109a89290>,
 'c3-answerkey': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c3-answerkey'}) at 0x109a89350>,
 'notes': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'notes'}) at 0x109a893d0>}

>>> book.spine.list()
[<Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'intro'}) at 0x107533c90>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c1'}) at 0x109a88ed0>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c1-answerkey'}) at 0x109a88f50>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c2'}) at 0x109a89110>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c2-answerkey'}) at 0x109a891d0>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c3'}) at 0x109a89290>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c3-answerkey'}) at 0x109a89350>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'notes'}) at 0x109a893d0>]
```

Get an itemref

```python
>>> book.spine[0]
<Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'intro'}) at 0x107533c90>

>>>book.manifest['intro'] 
<Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'intro'}) at 0x107533c90>
```

Add a file

```python
>>> item = book.manifest.add("chapter0001.xhtml", id="chapter0001")
>>> item
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'chapter0001', 'href': 'chapter0001.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1079bb190>
```

Open and write some textual data to it

```python
>>> file = item.open("w")
>>> file
<_io.TextIOWrapper name='/var/folders/k1/3r19jl7d30n834vdmbz9ygh80000gn/T/tmpzubn_x2f/69bccdc4-50b5-404a-8117-33fe47648f3a' encoding='utf-8'>
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
```

Read it again

```python
>>> print(item.read_text())
<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title></title>
</head>
<body>
  <p>&#160;</p>
</body>
</html>
```

Add the item to spine

```python
>>> book.spine.add(item)
<Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'chapter0001'}) at 0x1133e4510>
```

Add an external file

```python
>>> item = book.manifest.add("features.js", "js/features.js")
>>> item
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c8d322e0-a960-44ea-bf15-66d1dbbce15d', 'href': 'features.js', 'media-type': 'text/javascript'}) at 0x1038db390>
```

Add a `dc:creator` metadata

```python
>>> book.metadata.add("dc:creator", dict(id="creator"), text="ChenyangGao")
<DCTerm(<{http://purl.org/dc/elements/1.1/}creator>, attrib={'id': 'creator'}, text='ChenyangGao') at 0x103ced950>
```

Add a `<meta>` metadata

```python
>>> book.metadata.add("meta", dict(refines="#creator", property="role", scheme="marc:relators", id="role"), text="author")
<Meta(<{http://www.idpf.org/2007/opf}meta>, attrib={'refines': '#creator', 'property': 'role', 'scheme': 'marc:relators', 'id': 'role'}, text='author') at 0x105128a50>
```

Find metadata

```python
>>> book.metadata.find("dc:creator")
<DCTerm(<{http://purl.org/dc/elements/1.1/}creator>, attrib={'id': 'creator'}, text='ChenyangGao') at 0x103ced950>
>>> book.metadata.dc("creator")
<DCTerm(<{http://purl.org/dc/elements/1.1/}creator>, attrib={'id': 'creator'}, text='ChenyangGao') at 0x103ced950>
>>> book.metadata.meta('[@property="role"]')
<Meta(<{http://www.idpf.org/2007/opf}meta>, attrib={'refines': '#creator', 'property': 'role', 'scheme': 'marc:relators', 'id': 'role'}, text='author') at 0x105128a50>
>>> book.metadata.property_meta("role")
<Meta(<{http://www.idpf.org/2007/opf}meta>, attrib={'refines': '#creator', 'property': 'role', 'scheme': 'marc:relators', 'id': 'role'}, text='author') at 0x105128a50>
```

Pack the book

```python
>>> book.pack("book_i_made.epub")
```

View [tutorial](https://python-epub3.readthedocs.io/en/latest/tutorial.html) for more details.

## Features

- Proxy underlying XML element nodes to operate on OPF document.
- Support querying nodes using [ElementPath](https://docs.python.org/3/library/xml.etree.elementtree.html#supported-xpath-syntax).
- Manifest supports file system interfaces, referenced [os.path](https://docs.python.org/3/library/os.path.html), [shutil](https://docs.python.org/3/library/shutil.html), [pathlib.Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path).
- Numerous lazy loading features, just like [Occam's razor](https://en.wikipedia.org/wiki/Occam%27s_razor).
    > Entities should not be multiplied unnecessarily.  
    > <span style="text-align: right; display: block">-- **Occam's razor**</span>

    > We are to admit no more causes of natural things than such as are both true and sufficient to explain their appearances.  
    > <span style="text-align: right; display: block">-- **Isaac Newton**</span>

    > Everything should be made as simple as possible, but no simpler.  
    > <span style="text-align: right; display: block">-- **Albert Einstein**</span>
- Caching instance, not created repeatedly, and recycled in a timely manner.
- Allow adding any openable files, as long as there is an open method and its parameters are compatible with [open](https://docs.python.org/3/library/functions.html#open).
- Stream processing, supporting various operators such as **map**, **reduce**, **filter**, etc.
- Various proxies and bindings fully realize multiple ways to achieve the same operational objective.

## Documentation

[https://python-epub3.readthedocs.io](https://python-epub3.readthedocs.io)
