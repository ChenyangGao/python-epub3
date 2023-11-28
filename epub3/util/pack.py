#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__all__ = ["pack_epub", "pack_sphinx_epub"]

import os.path as ospath
import posixpath

from collections import deque
from datetime import datetime
from glob import iglob
from itertools import count
from mimetypes import guess_type
from os import fsdecode, listdir, PathLike
from pathlib import Path
from typing import (
    cast, Callable, Container, Final, Iterator, Optional, Sequence, MutableSequence
)
from urllib.parse import urlsplit
from uuid import uuid4
from zipfile import ZipFile

from lxml.etree import fromstring as xml_fromstring, tostring, Element, _Comment, _Element
from lxml.html import fromstring as html_fromstring

from .xml_plus import to_xhtml


def oebps_iter(
    top: bytes | str | PathLike, 
    filter: Optional[Callable[[Path], bool]] = None, 
    follow_symlinks: bool = True, 
    on_error: None | bool | Callable = None, 
) -> Iterator[tuple[str, Path]]:
    """Iterate over the directory structure starting from `top` (exclusive), 
    yield a tuple of two paths each time, one is a relative path based on `top`, 
    the other is the corresponding actual path object (does not include a directory).

    Note: This function uses breadth-first search (bfs) to iterate over the directory structure.

    :param top: The directory path to start the iteration from.
    :param filter: A callable that takes a Path object as input and returns True 
                   if the path should be included, or False otherwise.
    :param follow_symlinks: If True, symbolic links will be followed during iteration.
    :param on_error: A callable to handle any error encountered during iteration.

    :yield: A tuple containing the href (a relative path based on `top`) and the corresponding Path object.
    """
    dq: deque[tuple[str, Path]] = deque()
    put, get = dq.append, dq.popleft
    put(("", Path(fsdecode(top))))
    while dq:
        dir_, top = dq.popleft()
        try:
            path_iterable = top.iterdir()
        except OSError as e:
            if callable(on_error):
                on_error(e)
            elif on_error:
                raise
            continue
        for path in path_iterable:
            if path.is_symlink() and not follow_symlinks or filter and not filter(path):
                continue
            href = dir_ + "/" + path.name if dir_ else path.name
            if path.is_dir():
                put((href, path))
            else:
                yield href, path


def pack_epub(
    source_dir: bytes | str | PathLike, 
    save_path: None | bytes | str | PathLike = None, 
    generate_id: Callable[[str], str] = lambda href: str(uuid4()), 
    content_opf: None | bytes | str | _Element = None, 
    spine_files: None | Sequence | Container | Callable = None, 
    filter: Optional[Callable[[Path], bool]] = lambda path: (
        path.name not in (".DS_Store", "Thumbs.db") and
        not path.name.startswith("._")
    ), 
    follow_symlinks: bool = True, 
    sort: Optional[Callable] = None, 
    finalize: Optional[Callable] = None, 
) -> bytes | str | PathLike:
    """This function is used to pack a directory of files into an ePub format e-book. 

    :param source_dir: The source directory containing the files to be packaged.
    :param save_path: The path where the ePub file will be saved. If not provided, it will be 
                      saved in the same directory as the source with the .epub extension.
    :param generate_id: A function to generate unique identifiers for items in the ePub file.
    :param content_opf: An optional parameter representing the original content.opf file of the ePub.
    :param spine_files: An optional parameter to determine which (HTML or XHTML) files of the ePub 
                        should be included in the spine. 
    :param filter: An optional function used to filter the files to be included in the ePub.
    :param follow_symlinks: A boolean indicating whether to follow symbolic links.
    :param sort: An optional function to sort the files before packaging.
    :param finalize: An optional function to perform a finalization step at end of packaging.

    :return: The path where the ePub file is saved.

    Note:
        - The spine_files parameter serves as a predicate to determine which files should be included 
          in the linear reading order (spine) of the ePub. 
        - The spine_files is a sequence, container, or callable, it is used to specify the inclusion 
          criteria for files in the spine.
        - If spine_files is a sequence, it also determines the order of the spine.
    """
    source_dir = ospath.abspath(fsdecode(source_dir))
    if not save_path:
        save_path = source_dir + ".epub"
    if isinstance(content_opf, _Element):
        opf_etree = content_opf.getroottree().getroot()
    elif content_opf:
        opf_etree = xml_fromstring(content_opf)
    elif ospath.isfile(ospath.join(source_dir, "content.opf")):
        opf_etree = xml_fromstring(open(ospath.join(source_dir, "content.opf"), "rb").read())
    else:
        opf_etree = xml_fromstring(b'''\
<?xml version="1.0" encoding="utf-8"?>
<package version="3.0" unique-identifier="BookId" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="BookId">urn:uuid:%(uuid)s</dc:identifier>
    <dc:language>en</dc:language>
    <dc:title>untitled</dc:title>
    <meta property="dcterms:modified">%(mtime)s</meta>
  </metadata>
  <manifest />
  <spine />
</package>''' % {
    b"uuid": bytes(str(uuid4()), "utf-8"), 
    b"mtime": bytes(datetime.now().strftime("%FT%XZ"), "utf-8"), 
})
    opf_manifest = opf_etree[1]
    opf_spine = opf_etree[2]
    id_2_item: dict[str, _Element] = {el.attrib["id"]: el for el in opf_manifest if "href" in el.attrib} # type: ignore
    href_2_id_cache = {el.attrib["href"]: id for id, el in id_2_item.items()}
    spine_map: dict[str, Optional[_Element]] = {
        id_2_item[el.attrib["idref"]].attrib["href"]: el # type: ignore
        for el in opf_spine if el.attrib["idref"] in id_2_item
    }
    is_spine: Optional[Callable] = None
    if isinstance(spine_files, Sequence):
        # NOTE: If spine_files is a sequence and immutable, then the spine will 
        #       consist of at most the items in this sequence.
        for href in spine_files:
            if href not in spine_map:
                spine_map[href] = None
        if isinstance(spine_files, MutableSequence):
            is_spine = lambda href: href.endswith((".htm", ".html", ".xhtm", ".xhtml"))
    elif isinstance(spine_files, Container):
        is_spine = lambda href: href in spine_files # type: ignore
    elif callable(spine_files):
        is_spine = spine_files
    it = oebps_iter(source_dir, filter=filter, follow_symlinks=follow_symlinks)
    if sort:
        it = sort(it)
    with ZipFile(save_path, "w") as book: # type: ignore
        book.writestr("mimetype", "application/epub+zip")
        book.writestr("META-INF/container.xml", '''\
<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
   </rootfiles>
</container>''')
        for href, path in it:
            if href == "content.opf":
                continue
            media_type = guess_type(href)[0] or "application/octet-stream"
            if href in href_2_id_cache:
                uid  = href_2_id_cache.pop(href)
                item = id_2_item[uid]
                if "media-type" not in item.attrib:
                    item.attrib["media-type"] = media_type
            else:
                uid = str(generate_id(href))
                if uid in id_2_item:
                    nuid = str(generate_id(href))
                    if uid == nuid:
                        for i in count(1):
                            nuid = f"{i}_{uid}"
                            if nuid not in id_2_item:
                                uid = nuid
                                break
                    else:
                        uid = nuid
                        while uid in id_2_item:
                            uid = str(generate_id(href))
                id_2_item[uid] = Element("item", attrib={"id": uid, "href": href, "media-type": media_type})
            book_path = "OEBPS/" + href
            if href.endswith((".htm", ".html")):
                etree = html_fromstring(open(path, "rb").read())
                tostr = to_xhtml(etree, ensure_epub=True)
                book.writestr(book_path, tostr())
            else:
                book.write(path, book_path)
            if href in spine_map and spine_map[href] is None or is_spine and is_spine(href):
                spine_map[href] = Element("itemref", attrib={"idref": uid})
        opf_manifest.clear()
        for uid in href_2_id_cache.values():
            item = id_2_item.pop(uid)
            print("\x1b[38;5;6m\x1b[1mIGNORE\x1b[0m: item has been ignored because file not found: "
                f"\n    |_ href={item.attrib['href']!r}"
                f"\n    |_ item={tostring(item).decode('utf-8')!r}")
        opf_manifest.extend(el for el in id_2_item.values())
        opf_spine.clear()
        opf_spine.extend(el for el in spine_map.values() if el is not None)
        if finalize:
            finalize(book, opf_etree)
        book.writestr("OEBPS/content.opf", 
            b'<?xml version="1.0" encoding="UTF-8"?>\n'+tostring(opf_etree, encoding="utf-8"))
    return save_path


def pack_sphinx_epub(
    source_dir: bytes | str | PathLike, 
    save_path: None | bytes | str | PathLike = None, 
    follow_symlinks: bool = True, 
    sort: Optional[Callable] = None, 
) -> bytes | str | PathLike:
    """Pack a Sphinx documentation into ePub format.

    NOTE: If there are references to online resources, please localize them in advance.

    :param source_dir: Path to the source directory.
    :param save_path: Path where the ePub file will be saved. If not provided, it will be 
                      saved in the same directory as the source with the .epub extension.
    :param follow_symlinks: A boolean indicating whether to follow symbolic links.
    :param sort: An optional function to sort the files before packaging.

    :return: Path to the saved ePub file.
    """
    def clean_toc(el):
        tag = el.tag.lower()
        if tag == "ul":
            el.tag = "ol"
        if tag == "a":
            href = el.attrib.get("href", "")
            el.attrib.clear()
            el.attrib["href"] = href
        else:
            el.attrib.clear()
        for sel in el:
            if sel.tag.lower() in ("ul", "li", "a", "ol"):
                clean_toc(sel)
            else:
                el.remove(sel)
        return el
    def finalize(book, opf_etree):
        opf_metadata = opf_etree[0]
        opf_manifest = opf_etree[1]
        opf_spine = opf_etree[2]
        # add nav.xhtml
        if "OEBPS/nav.html" in book.NameToInfo and "OEBPS/nav.xhtml" not in book.NameToInfo:
            etree = html_fromstring(book.read("OEBPS/nav.html"))
            toc_org = etree.get_element_by_id("toc")
            if toc_org is None or len(toc_org) == 0:
                toc = None
            else:
                toc = clean_toc(toc_org[0])
            nav = html_fromstring(b'''\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>ePub NAV</title>
  <meta charset="utf-8" />
</head>
<body epub:type="frontmatter">
  <nav epub:type="toc" id="toc" role="doc-toc">
    <h1>Table of Contents</h1>
  </nav>
  <nav epub:type="landmarks" id="landmarks" hidden="">
    <h2>Landmarks</h2>
    <ol>
      <li>
        <a epub:type="toc" href="#toc">Table of Contents</a>
      </li>
    </ol>
  </nav>
</body>
</html>''')
            if toc is not None:
                toc_tgt = nav.xpath('//*[@id="toc"]')[0]
                toc_tgt.append(toc)
            book.writestr("OEBPS/nav.xhtml", tostring(
                nav, encoding="utf-8", xml_declaration='<?xml version="1.0" encoding="utf-8"?>'))
            opf_manifest.append(Element("item", attrib={
                "id": "nav.xhtml", "href": "nav.xhtml", "media-type": "application/xhtml+xml", "properties": "nav"}))
            opf_spine.append(Element("itemref", attrib={"idref": "nav.xhtml", "linear": "no"}))
        # set cover
        for item in opf_manifest:
            if not item.attrib["media-type"].startswith("image/"):
                continue
            href = item.attrib["href"]
            name = posixpath.splitext(posixpath.basename(href))[0]
            if name != "cover":
                continue
            uid = item.attrib["id"]
            try:
                cover_meta = opf_etree.xpath('//*[local-name()="meta"][@name="cover"]')[0]
                cover_meta.attrib["content"] = uid
            except IndexError:
                cover_meta = Element("meta", attrib={"name": "cover", "content": uid})
                opf_metadata.append(cover_meta)
        # set title
        opf_metadata.find("dc:title", opf_metadata.nsmap).text = index_etree.head.find('title').text
    source_dir = ospath.abspath(fsdecode(source_dir))
    if not save_path:
        save_path = source_dir + ".epub"
    if "index.html" in listdir(source_dir):
        index_html_path = ospath.join(source_dir, "index.html")
    else:
        index_html_path = ospath.join(source_dir, 
            next(iglob("**/index.html", root_dir=source_dir, recursive=True)))
        source_dir = ospath.dirname(index_html_path)
    index_etree = html_fromstring(open(index_html_path, "rb").read())
    spine_files = ["index.html", "nav.html"]
    seen = set(spine_files)
    for el in index_etree.cssselect('li[class^="toctree-l"] > a[href]'):
        href: str = el.attrib["href"] # type: ignore
        urlp = urlsplit(href)
        if urlp.scheme or urlp.netloc:
            continue
        href = urlp.path
        if href in seen:
            continue
        spine_files.append(href)
        seen.add(href)
    pack_epub(
        source_dir, 
        save_path, 
        generate_id=posixpath.basename, 
        spine_files=spine_files, 
        filter=lambda path: path.name != "Thumbs.db" and 
                            not path.name.startswith(".") and 
                            not path.name.endswith((".js.map", ".css.map")), 
        follow_symlinks=follow_symlinks, 
        sort=sort, 
        finalize=finalize, 
    )
    return save_path

# TODO: This module needs optimization

