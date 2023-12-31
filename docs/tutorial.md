# Tutorial

## Introduction

[python-epub3](https://github.com/ChenyangGao/python-epub3) is a Python library for managing ePub 3 books, even though it can also be used to operate ePub 2.

Install through [github](https://github.com/ChenyangGao/python-epub3):

```shell
pip install git+https://github.com/ChenyangGao/python-epub3
```

Install through [pypi](https://pypi.org/project/python-epub3/):

```shell
pip install python-epub3
```

## Reading ePub

```python
from epub3 import ePub

book = ePub("sample.epub")
```

There is a {py:class}`epub3.ePub` class used for operating ePub files. It accepts a optional file path to the ePub file as argument.

Let's say the `sample.epub` with the `content.opf` file content is

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

### Package document

The [package document](https://www.w3.org/TR/epub/#dfn-package-document) is an XML document that consists of a set of elements that each encapsulate information about a particular aspect of an [EPUB publication](https://www.w3.org/TR/epub/#dfn-epub-publication). These elements serve to centralize metadata, detail the individual resources, and provide the reading order and other information necessary for its rendering.

The following list summarizes the information found in the [package](https://www.w3.org/TR/epub/#sec-package-doc) document:

- [Metadata](https://www.w3.org/TR/epub/#sec-pkg-metadata) — mechanisms to include and/or reference information about the EPUB publication.
- A [manifest](https://www.w3.org/TR/epub/#sec-manifest-elem) — identifies via URL [[url](https://www.w3.org/TR/epub/#bib-url)], and describes via MIME media type [[rfc4839](https://www.w3.org/TR/epub/#bib-rfc4839)], the set of [publication resources](https://www.w3.org/TR/epub/#dfn-publication-resource).
- A [spine](https://www.w3.org/TR/epub/#sec-spine-elem) — an ordered sequence of ID references to top-level resources in the manifest from which [reading systems](https://www.w3.org/TR/epub/#dfn-epub-reading-system) can reach or utilize all other resources in the set. The spine defines the default reading order.
- [Collections](https://www.w3.org/TR/epub/#sec-collection-elem) — a method of encapsulating and identifying subcomponents within the EPUB publication.
- [Manifest fallback chains](https://www.w3.org/TR/epub/#dfn-manifest-fallback-chain) — a mechanism that defines an ordered list of top-level resources as content equivalents. A reading system can then choose between the resources based on which it is capable of rendering.

### Metadata

The [`metadata`](https://www.w3.org/TR/epub/#sec-pkg-metadata) element encapsulates meta information.

The [package document](https://www.w3.org/TR/epub/#dfn-package-document) `metadata` element has two primary functions:

1. to provide a minimal set of meta information for [reading systems](https://www.w3.org/TR/epub/#dfn-epub-reading-system) to use to internally catalogue an [EPUB publication](https://www.w3.org/TR/epub/#dfn-epub-publication) and make it available to a user (e.g., to present in a bookshelf).
2. to provide access to all rendering metadata needed to control the layout and display of the content (e.g., [fixed-layout properties](https://www.w3.org/TR/epub/#sec-fxl-package)).

```{note}
The package document does not provide complex metadata encoding capabilities. If [EPUB creators](https://www.w3.org/TR/epub/#dfn-epub-creator) need to provide more detailed information, they can associate metadata records (e.g., that conform to an international standard such as [[onix](https://www.w3.org/TR/epub/#bib-onix)] or are created for custom purposes) using the `link` element. This approach allows reading systems to process the metadata in its native form, avoiding the potential problems and information loss caused by translating to use the minimal package document structure.
```

Property {py:attr}`epub3.ePub.metadata` is used for fetching metadata. It is an instance of type {py:class}`epub3.Metadata`.

#### Dublin Core required elements

Minimal required metadata elements from [DCMES](https://www.w3.org/TR/epub/#sec-opf-dcmes-required) ([**D**ublin **C**ore](https://www.dublincore.org/specifications/dublin-core/) **M**etadata **E**lement **S**et) is:

- **dc:identifier** contains an identifier such as a <kbd>UUID</kbd>, <kbd>DOI</kbd> or <kbd>ISBN</kbd>.
- **dc:title** represents an instance of a name for the [EPUB publication](https://www.w3.org/TR/epub/#dfn-epub-publication).
- **dc:language** specifies the language of the content of the [EPUB publication](https://www.w3.org/TR/epub/#dfn-epub-publication).

The `dc` prefix namespace represents the URI `http://purl.org/dc/elements/1.1/` and is used when accessing Dublin Core metadata.

The minimal set of metadata required in the package document is defined inside of content.opf file.

```xml
<package unique-identifier="pub-id">
    <metadata>
       <dc:identifier id="pub-id">urn:uuid:bb4d4afe-f787-4d21-97b8-68f6774ba342</dc:identifier>
       <dc:title>ePub</dc:title>
       <dc:language>en</dc:language>
       <meta property="dcterms:modified">2989-06-04T00:00:00Z</meta>
    </metadata>
</package>
```

```python
>>> book.metadata.dc('identifier')
<DCTerm(<{http://purl.org/dc/elements/1.1/}identifier>, attrib={'id': 'BookId'}, text='urn:uuid:bb4d4afe-f787-4d21-97b8-68f6774ba342') at 0x105338210>

>>> book.metadata.dc('title')
<DCTerm(<{http://purl.org/dc/elements/1.1/}title>, text='ePub') at 0x105313fd0>

>>> book.metadata.dc('language')
<DCTerm(<{http://purl.org/dc/elements/1.1/}language>, text='en') at 0x105357550>

>>> book.metadata.meta('[@property="dcterms:modified"]')
<Meta(<{http://www.idpf.org/2007/opf}meta>, attrib={'property': 'dcterms:modified'}, text='2989-06-04T00:00:00Z') at 0x10532dd90>
```

You can also use these properties to quickly obtain

```python
>>> book.identifier
'urn:uuid:bb4d4afe-f787-4d21-97b8-68f6774ba342'

>>> book.title
'ePub'

>>> book.language
'en'
```

#### Dublin Core optional elements

All [[dcterms](https://www.w3.org/TR/epub/#bib-dcterms)] elements except for `dc:identifier`, `dc:language`, and `dc:title` are designated as [*OPTIONAL*](https://www.w3.org/TR/epub/#sec-opf-dcmes-optional).

| Properties in the `/terms/` namespace:        | [abstract](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/abstract), [accessRights](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/accessRights), [accrualMethod](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/accrualMethod), [accrualPeriodicity](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/accrualPeriodicity), [accrualPolicy](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/accrualPolicy), [alternative](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/alternative), [audience](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/audience), [available](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/available), [bibliographicCitation](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/bibliographicCitation), [conformsTo](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/conformsTo), [contributor](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/contributor), [coverage](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/coverage), [created](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/created), [creator](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/creator), [date](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/date), [dateAccepted](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/dateAccepted), [dateCopyrighted](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/dateCopyrighted), [dateSubmitted](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/dateSubmitted), [description](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/description), [educationLevel](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/educationLevel), [extent](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/extent), [format](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/format), [hasFormat](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/hasFormat), [hasPart](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/hasPart), [hasVersion](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/hasVersion), [identifier](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/identifier), [instructionalMethod](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/instructionalMethod), [isFormatOf](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/isFormatOf), [isPartOf](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/isPartOf), [isReferencedBy](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/isReferencedBy), [isReplacedBy](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/isReplacedBy), [isRequiredBy](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/isRequiredBy), [issued](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/issued), [isVersionOf](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/isVersionOf), [language](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/language), [license](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/license), [mediator](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/mediator), [medium](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/medium), [modified](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/modified), [provenance](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/provenance), [publisher](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/publisher), [references](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/references), [relation](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/relation), [replaces](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/replaces), [requires](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/requires), [rights](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/rights), [rightsHolder](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/rightsHolder), [source](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/source), [spatial](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/spatial), [subject](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/subject), [tableOfContents](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/tableOfContents), [temporal](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/temporal), [title](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/title), [type](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/type), [valid](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/valid) |
| --------------------------------------------- | ------------------------------------------------------------ |
| Properties in the `/elements/1.1/` namespace: | [contributor](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/contributor), [coverage](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/coverage), [creator](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/creator), [date](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/date), [description](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/description), [format](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/format), [identifier](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/identifier), [language](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/language), [publisher](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/publisher), [relation](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/relation), [rights](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/rights), [source](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/source), [subject](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/subject), [title](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/title), [type](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/elements/1.1/type) |
| Vocabulary Encoding Schemes:                  | [DCMIType](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/DCMIType), [DDC](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/DDC), [IMT](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/IMT), [LCC](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/LCC), [LCSH](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/LCSH), [MESH](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/MESH), [NLM](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/NLM), [TGN](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/TGN), [UDC](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/UDC) |
| Syntax Encoding Schemes:                      | [Box](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/Box), [ISO3166](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/ISO3166), [ISO639-2](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/ISO639-2), [ISO639-3](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/ISO639-3), [Period](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/Period), [Point](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/Point), [RFC1766](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/RFC1766), [RFC3066](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/RFC3066), [RFC4646](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/RFC4646), [RFC5646](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/RFC5646), [URI](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/URI), [W3CDTF](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/W3CDTF) |
| Classes:                                      | [Agent](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/Agent), [AgentClass](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/AgentClass), [BibliographicResource](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/BibliographicResource), [FileFormat](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/FileFormat), [Frequency](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/Frequency), [Jurisdiction](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/Jurisdiction), [LicenseDocument](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/LicenseDocument), [LinguisticSystem](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/LinguisticSystem), [Location](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/Location), [LocationPeriodOrJurisdiction](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/LocationPeriodOrJurisdiction), [MediaType](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/MediaType), [MediaTypeOrExtent](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/MediaTypeOrExtent), [MethodOfAccrual](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/MethodOfAccrual), [MethodOfInstruction](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/MethodOfInstruction), [PeriodOfTime](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/PeriodOfTime), [PhysicalMedium](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/PhysicalMedium), [PhysicalResource](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/PhysicalResource), [Policy](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/Policy), [ProvenanceStatement](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/ProvenanceStatement), [RightsStatement](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/RightsStatement), [SizeOrDuration](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/SizeOrDuration), [Standard](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/terms/Standard) |
| DCMI Type Vocabulary:                         | [Collection](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/Collection), [Dataset](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/Dataset), [Event](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/Event), [Image](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/Image), [InteractiveResource](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/InteractiveResource), [MovingImage](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/MovingImage), [PhysicalObject](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/PhysicalObject), [Service](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/Service), [Software](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/Software), [Sound](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/Sound), [StillImage](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/StillImage), [Text](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcmitype/Text) |
| Terms for vocabulary description:             | [domainIncludes](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcam/domainIncludes), [memberOf](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcam/memberOf), [rangeIncludes](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcam/rangeIncludes), [VocabularyEncodingScheme](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/#http://purl.org/dc/dcam/VocabularyEncodingScheme) |

#### The `meta` element

The [`meta`](https://www.w3.org/TR/epub/#sec-meta-elem) element provides a generic means of including package metadata.

Each `meta` element defines a metadata expression. The `property` attribute takes a [property data type value](https://www.w3.org/TR/epub/#sec-property-datatype) that defines the statement made in the expression, and the text content of the element represents the assertion. (Refer to [D.1 Vocabulary association mechanisms](https://www.w3.org/TR/epub/#sec-vocab-assoc) for more information.)

[This specification](https://www.w3.org/TR/epub/#sec-meta-elem) defines two types of metadata expressions that [EPUB creators](https://www.w3.org/TR/epub/#dfn-epub-creator) can define using the `meta` element:

- A *primary expression* is one in which the expression defined in the `meta` element establishes some aspect of the [EPUB publication](https://www.w3.org/TR/epub/#dfn-epub-publication). A `meta` element that omits a refines attribute defines a primary expression.
- A *subexpression* is one in which the expression defined in the `meta` element is associated with another expression or resource using the `refines` attribute to enhance its meaning. A subexpression might refine a media clip, for example, by expressing its duration, or refine a creator or contributor expression by defining the role of the person.

```{note}
EPUB creators *MAY* use subexpressions to refine the meaning of other subexpressions, thereby creating chains of information.

All the [[dcterms](https://www.w3.org/TR/epub/#bib-dcterms)] elements represent primary expressions, and permit refinement by meta element subexpressions.
```

```{note}
The [Meta Properties Vocabulary](https://www.w3.org/TR/epub/#app-meta-property-vocab) is the [default vocabulary](https://www.w3.org/TR/epub/#sec-default-vocab) for use with the `property` attribute.

EPUB creators *MAY* add terms from other vocabularies as defined in [D.1 Vocabulary association mechanisms](https://www.w3.org/TR/epub/#sec-vocab-assoc).
```

You can also have custom metadata. For instance this is how custom metadata is defined in `content.opf` file. You can define same key more than once.

```xml
<dc:creator id="creator">ChengyangGao</dc:creator>
<meta refines="#creator" property="role" scheme="marc:relators">author</meta>
<meta refines="#creator" property="file-as" scheme="marc:relators">author</meta>
```

```python
book.metadata.add("dc:creator", dict(id="creator"), text="ChenyangGao")
book.metadata.add("meta", dict(refines="#creator", property="role", scheme="marc:relators", id="role"), text="author")
book.metadata.add("meta", dict(refines="#creator", property="file-as", scheme="marc:relators", id="file-as"), text="author")
```

To get all `<meta>`, you can do as the following

```python
>>> book.metadata.iterfind('meta').list()
[<Meta(<{http://www.idpf.org/2007/opf}meta>, attrib={'property': 'dcterms:modified'}, text='2989-06-04T00:00:00Z') at 0x10532dd90>,
 <Meta(<{http://www.idpf.org/2007/opf}meta>, attrib={'refines': '#creator', 'property': 'role', 'scheme': 'marc:relators', 'id': 'role'}, text='author') at 0x1053ee3d0>,
 <Meta(<{http://www.idpf.org/2007/opf}meta>, attrib={'refines': '#creator', 'property': 'file-as', 'scheme': 'marc:relators', 'id': 'file-as'}, text='author') at 0x105e15610>]
```

```{note}
The {py:meth}`Metadata.iterfind` method uses [ElementPath](https://docs.python.org/3/library/xml.etree.elementtree.html#supported-xpath-syntax) to retrieve child nodes.
```

Check the official documentation for more info:

- [https://www.w3.org/TR/epub/#sec-pkg-metadata](https://www.w3.org/TR/epub/#sec-pkg-metadata)
- [https://www.dublincore.org/specifications/dublin-core/dcmi-terms/](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/)
- [https://www.dublincore.org/specifications/dublin-core/dces/](https://www.dublincore.org/specifications/dublin-core/dces/)

#### The `link` element

The `link` element associates resources with an [EPUB publication](https://www.w3.org/TR/epub/#dfn-epub-publication), such as metadata records.

The `metadata` element *MAY* contain zero or more `link` elements, each of which identifies the location of a [publication resource](https://www.w3.org/TR/epub/#dfn-publication-resource) or a [linked resource](https://www.w3.org/TR/epub/#dfn-linked-resource) in its *REQUIRED* `href` attribute.

Resources referenced from the `link` element are [publication resources](https://www.w3.org/TR/epub/#dfn-publication-resource) only when they are:

- referenced from the [spine](https://www.w3.org/TR/epub/#dfn-epub-spine); or
- included or embedded in an [EPUB content document](https://www.w3.org/TR/epub/#dfn-epub-content-document) (e.g., a metadata record serialized as RDFa [[rdfa-core](https://www.w3.org/TR/epub/#bib-rdfa-core)] or as JSON-LD [[json-ld11](https://www.w3.org/TR/epub/#bib-json-ld11)] embedded in an [[html](https://www.w3.org/TR/epub/#bib-html)] `script` element).

In all other cases (e.g., when linking to standalone [[onix](https://www.w3.org/TR/epub/#bib-onix)] records), the resources referenced are not [publication resources](https://www.w3.org/TR/epub/#dfn-publication-resource) (i.e., are not subject to [core media type requirements](https://www.w3.org/TR/epub/#sec-core-media-types)) and [EPUB creators](https://www.w3.org/TR/epub/#dfn-epub-creator) *MUST NOT* list them in the [manifest](https://www.w3.org/TR/epub/#sec-manifest-elem).

### Manifest

The [`manifest`](https://www.w3.org/TR/epub/#sec-pkg-manifest) element provides an exhaustive list of [publication resources](https://www.w3.org/TR/epub/#dfn-publication-resource) used in the rendering of the content.

With the exception of the [package document](https://www.w3.org/TR/epub/#dfn-package-document), the `manifest` *MUST* list all publication resources regardless of whether they are [container resources](https://www.w3.org/TR/epub/#dfn-container-resource) or [remote resources](https://www.w3.org/TR/epub/#dfn-remote-resource).

As the package document is already identified by the [`container.xml` file](https://www.w3.org/TR/epub/#sec-container-metainf-container.xml), the `manifest` *MUST NOT* specify an `item` element for it (i.e., a self-reference serves no purpose).

```{note}
The manifest is only for listing publication resources. [Linked resources](https://www.w3.org/TR/epub/#dfn-linked-resource) and [the special files for processing the OCF Container](https://www.w3.org/TR/epub/#sec-container-file-and-dir-structure) (i.e., files in the `META-INF` directory, and the `mimetype` file) are restricted from inclusion.

Failure to provide a complete manifest of publication resources may lead to rendering issues. [Reading systems](https://www.w3.org/TR/epub/#dfn-epub-reading-system) might not unzip such resources or could prevent access to them for security reasons.
```

Property {py:attr}`epub3.ePub.manifest` is used for fetching manifest. It is an instance of type {py:class}`epub3.Manifest`.

#### The `item` element

The [`item`](https://www.w3.org/TR/epub/#sec-item-elem) element represents a [publication resource](https://www.w3.org/TR/epub/#dfn-publication-resource).

The `epub3.ePub.manifest` contains a series of items that are wrapped by the {py:class}`epub3.Item` class.

Each item element has 3 required attributes: `id`, `href` and `media-type`.

```xml
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
      href="./images/cover.svg"
      properties="cover-image"
      media-type="image/svg+xml"/>
  <item
      id="f1"
      href="./images/fig1.jpg"
      media-type="image/jpeg"/>
  <item
      id="f2"
      href="./images/fig2.jpg"
      media-type="image/jpeg"/>
  <item
      id="css"
      href="./style/book.css"
      media-type="text/css"/>
</manifest>
```

```python
>>> book.manifest
{'nav': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x105324910>,
 'intro': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'intro', 'href': 'intro.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105324ed0>,
 'c1': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c1', 'href': 'chap1.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325650>,
 'c1-answerkey': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c1-answerkey', 'href': 'chap1-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325790>,
 'c2': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c2', 'href': 'chap2.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325850>,
 'c2-answerkey': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c2-answerkey', 'href': 'chap2-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325f90>,
 'c3': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c3', 'href': 'chap3.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1053267d0>,
 'c3-answerkey': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c3-answerkey', 'href': 'chap3-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105327450>,
 'notes': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'notes', 'href': 'notes.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1053274d0>,
 'cover': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'cover', 'href': 'images/cover.svg', 'properties': 'cover-image', 'media-type': 'image/svg+xml'}) at 0x105327a50>,
 'f1': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f1', 'href': 'images/fig1.jpg', 'media-type': 'image/jpeg'}) at 0x105355410>,
 'f2': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f2', 'href': 'images/fig2.jpg', 'media-type': 'image/jpeg'}) at 0x105563c10>,
 'css': <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'css', 'href': 'style/book.css', 'media-type': 'text/css'}) at 0x105560a50>}

>>> book.manifest.list()
[<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x105324910>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'intro', 'href': 'intro.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105324ed0>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c1', 'href': 'chap1.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325650>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c1-answerkey', 'href': 'chap1-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325790>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c2', 'href': 'chap2.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325850>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c2-answerkey', 'href': 'chap2-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325f90>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c3', 'href': 'chap3.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1053267d0>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c3-answerkey', 'href': 'chap3-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105327450>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'notes', 'href': 'notes.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1053274d0>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'cover', 'href': 'images/cover.svg', 'properties': 'cover-image', 'media-type': 'image/svg+xml'}) at 0x105327a50>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f1', 'href': 'images/fig1.jpg', 'media-type': 'image/jpeg'}) at 0x105355410>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f2', 'href': 'images/fig2.jpg', 'media-type': 'image/jpeg'}) at 0x105563c10>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'css', 'href': 'style/book.css', 'media-type': 'text/css'}) at 0x105560a50>]
```

You can retrieve an element from the manifest in various ways.

```python
>>> # by index
>>> item = book.manifest[0]
>>> item
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x105324910>

>>> # by item (itself)
>>> book.manifest[item]
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x105324910>

>>> # by id (to the item)
>>> book.manifest[item.id]
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x105324910>

>>> # by href (to the item)
>>> book.manifest(item.href)
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x105324910>
```

You can use {py:meth}`Manifest.filter_by_attrs` to filter items by a certain attribute (default to `'media-type'`).

```python
>>> # equal to this value: "image/jpeg"
>>> book.manifest.filter_by_attr("image/jpeg").list()
[<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f1', 'href': 'images/fig1.jpg', 'media-type': 'image/jpeg'}) at 0x105355410>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f2', 'href': 'images/fig2.jpg', 'media-type': 'image/jpeg'}) at 0x105563c10>]

>>> # starts with the specified prefix: "image"
>>> book.manifest.filter_by_attr("^image").list()
[<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'cover', 'href': 'images/cover.svg', 'properties': 'cover-image', 'media-type': 'image/svg+xml'}) at 0x105327a50>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f1', 'href': 'images/fig1.jpg', 'media-type': 'image/jpeg'}) at 0x105355410>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'f2', 'href': 'images/fig2.jpg', 'media-type': 'image/jpeg'}) at 0x105563c10>]

>>> # ends with the specified suffix: "xhtml+xml"
>>> book.manifest.filter_by_attr("$xhtml+xml").list()
[<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x105324910>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'intro', 'href': 'intro.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105324ed0>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c1', 'href': 'chap1.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325650>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c1-answerkey', 'href': 'chap1-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325790>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c2', 'href': 'chap2.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325850>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c2-answerkey', 'href': 'chap2-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105325f90>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c3', 'href': 'chap3.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1053267d0>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'c3-answerkey', 'href': 'chap3-answerkey.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105327450>,
 <Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'notes', 'href': 'notes.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x1053274d0>]
```

To open a file, you can use either the {py:meth}`Manifest.open` or {py:meth}`Item.open` method, which returns a file-like object, an instance of {py:class}`io.Base`.

```python
>>> item = book.manifest("nav.xhtml")
>>> item
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'nav', 'href': 'nav.xhtml', 'properties': 'nav', 'media-type': 'application/xhtml+xml'}) at 0x105324910>

>>> book.manifest.open(item.href)
<_io.TextIOWrapper name='/var/folders/k1/3r19jl7d30n834vdmbz9ygh80000gn/T/tmpjar2_4kv/4d4b73b9-61a9-4de4-b773-5ff752b920af' encoding='utf-8'>

>>> item.open()
<_io.TextIOWrapper name='/var/folders/k1/3r19jl7d30n834vdmbz9ygh80000gn/T/tmpjar2_4kv/4d4b73b9-61a9-4de4-b773-5ff752b920af' encoding='utf-8'>

>>> item.open("rb")
<_io.BufferedReader name='/var/folders/k1/3r19jl7d30n834vdmbz9ygh80000gn/T/tmpjar2_4kv/4d4b73b9-61a9-4de4-b773-5ff752b920af'>

>>> item.open("rb", buffering=0)
<_io.FileIO name='/var/folders/k1/3r19jl7d30n834vdmbz9ygh80000gn/T/tmpjar2_4kv/4d4b73b9-61a9-4de4-b773-5ff752b920af' mode='rb' closefd=True>
```

### Spine

The [`spine`](https://www.w3.org/TR/epub/#sec-spine-elem) element defines an ordered list of [manifest `item` references](https://www.w3.org/TR/epub/#sec-itemref-elem) that represent the default reading order.

The `spine` *MUST* specify at least one [EPUB content document](https://www.w3.org/TR/epub/#dfn-epub-content-document) or [foreign content document](https://www.w3.org/TR/epub/#dfn-foreign-content-document).

```{Important}
[EPUB creators](https://www.w3.org/TR/epub/#dfn-epub-creator) *MUST* list in the `spine` all EPUB and foreign content documents that are hyperlinked to from publication resources in the `spine`, where hyperlinking encompasses any linking mechanism that requires the user to navigate away from the current resource. Common hyperlinking mechanisms include the `href` attribute of the [[html](https://www.w3.org/TR/epub/#bib-html)] `a` and `area` elements and scripted links (e.g., using DOM Events and/or form elements). The requirement to list hyperlinked resources applies recursively (i.e., EPUB creators must list all EPUB and foreign content documents hyperlinked to from hyperlinked documents, and so on.).

EPUB creators also *MUST* list in the `spine` all EPUB and foreign content documents hyperlinked to from the [EPUB navigation document](https://www.w3.org/TR/epub/#dfn-epub-navigation-document), regardless of whether EPUB creators include the EPUB navigation document in the `spine`.
```

```{note}
As hyperlinks to resources outside the EPUB container are not [publication resources](https://www.w3.org/TR/epub/#dfn-publication-resource), they are not subject to the requirement to include in the spine (e.g., web pages and web-hosted resources).

Publication resources used in the rendering of spine items (e.g., referenced from [[html](https://www.w3.org/TR/epub/#bib-html)] [embedded content](https://html.spec.whatwg.org/multipage/dom.html#embedded-content-category)) similarly do not have to be included in the spine.
```

Property {py:attr}`epub3.ePub.spine` is used for fetching spine. It is an instance of type {py:class}`epub3.Spine`.

#### The itemref element

The `itemref` element identifies an [EPUB content document](https://www.w3.org/TR/epub/#dfn-epub-content-document) or [foreign content document](https://www.w3.org/TR/epub/#dfn-foreign-content-document) in the default reading order.

The `epub3.ePub.spine` contains a series of itemrefs that are wrapped by the {py:class}`epub3.Itemref` class.

Each itemref element has a required attribute: `idref`.

```{important}
Each `itemref` element *MUST* reference the [ID](https://www.w3.org/TR/xml/#id) [[xml](https://www.w3.org/TR/epub/#bib-xml)] of an `item` in the [manifest](https://www.w3.org/TR/epub/#dfn-epub-manifest) via the [IDREF](https://www.w3.org/TR/xml/#idref) [[xml](https://www.w3.org/TR/epub/#bib-xml)] in its `idref` attribute. `item` element IDs *MUST NOT* be referenced more than once.

Each referenced manifest `item` *MUST* be either a) an [EPUB content document](https://www.w3.org/TR/epub/#dfn-epub-content-document) or b) a [foreign content document](https://www.w3.org/TR/epub/#dfn-foreign-content-document) that includes an EPUB content document in its [manifest fallback chain](https://www.w3.org/TR/epub/#dfn-manifest-fallback-chain).
```

```{note}
Although [EPUB publications](https://www.w3.org/TR/epub/#dfn-epub-publication) [require an EPUB navigation document](https://www.w3.org/TR/epub/#confreq-nav), it is not mandatory to include it in the [spine](https://www.w3.org/TR/epub/#dfn-epub-spine).
```

```xml
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
```

```python
>>> book.spine
{'intro': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'intro'}) at 0x105574450>,
 'c1': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c1'}) at 0x105574510>,
 'c1-answerkey': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c1-answerkey'}) at 0x1055745d0>,
 'c2': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c2'}) at 0x105574690>,
 'c2-answerkey': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c2-answerkey'}) at 0x105574790>,
 'c3': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c3'}) at 0x105574890>,
 'c3-answerkey': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c3-answerkey'}) at 0x105574990>,
 'notes': <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'notes'}) at 0x105574a50>}

>>> book.spine.iter().list()
[<Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'intro'}) at 0x105574450>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c1'}) at 0x105574510>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c1-answerkey'}) at 0x1055745d0>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c2'}) at 0x105574690>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c2-answerkey'}) at 0x105574790>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c3'}) at 0x105574890>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'c3-answerkey'}) at 0x105574990>,
 <Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'notes'}) at 0x105574a50>]
```

You can retrieve an element from the spine in various ways.

```python
>>> # by index
>>> itemref = book.spine[0]
>>> itemref
<Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'intro'}) at 0x105574450>

>>> # by item
>>> item = book.manifest[itemref.idref]
>>> item
<Item(<{http://www.idpf.org/2007/opf}item>, attrib={'id': 'intro', 'href': 'intro.xhtml', 'media-type': 'application/xhtml+xml'}) at 0x105324ed0>
>>> book.spine[item]
<Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'intro'}) at 0x105574450>

>>> # by itemref (itself)
>>> book.spine[itemref]
<Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'intro'}) at 0x105574450>

>>> # by id (to the item)
>>> book.manifest[itemref.idref]
<Itemref(<{http://www.idpf.org/2007/opf}itemref>, attrib={'idref': 'intro'}) at 0x105574450>
```

## Writing ePub

...
