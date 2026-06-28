Software development benefits from
[philosophies](https://en.wikipedia.org/wiki/Category:Software_development_philosophies)
and [principles](https://en.wikipedia.org/wiki/Category:Programming_principles)
such as [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself),
[KISS](https://en.wikipedia.org/wiki/KISS_principle),
[code reuse](https://en.wikipedia.org/wiki/Code_reuse), and more. Developers use
these commonly understood standards to produce high-quality code.

These principles also apply to software _documentation_ to foster clean and
intuitive content that delights and empowers readers with easy-to-find
information.

## General documentation principles

All documentation should be…

### Precursory

_Begin documenting before you begin developing._

Before coding, write requirements and specifications that serve as the first
draft of documentation. These texts need a bit of cleanup before publishing, but
by front-loading the documentation, you lay a clear path forward. Early
documentation also helps facilitate peer feedback and group decisions to guide
your work. This model is the sentiment behind
[documentation driven design](https://www.writethedocs.org/guide/writing/style-guides#documentation-driven-design).

### Participatory

_In the documentation process, include everyone from developers to end users._

Integrate documentation into the standard workflow of developers, and reduce
silos that solicit documentation from only a subset of the software’s
contributors. Developers and engineers are the people with the best access to
in-demand information, and getting them to document it will help foster a
_culture_ of documentation.

Documentation _readers_ (i.e., users) should also have clear avenues towards
involvement in documentation. A good first step is to give readers the ability
to offer feedback through comments or suggestions. Allowing readers to edit
documentation directly (e.g., in a wiki) can also be effective but must be
weighed against the need and capacity for editorial oversight.

Encourage _everyone_ to become a
[documentarian](https://www.writethedocs.org/documentarians/)!

## Principles for great content

_“Content” is the conceptual information within documentation._

**Content** should be…

### ARID

_Accept (some) Repetition In Documentation._

If you want to write good code,
[Don’t Repeat Yourself](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself).
But if you adhere strictly to this DRY principle when writing documentation, you
won’t get far. _Some_ amount of business logic described by your code must be
described _again_ in your documentation.

In an ideal world, an automated system would generate documentation from the
software’s source code, _and_ the system would be smart enough to generate
_good_ documentation without any additional input. Unfortunately, today, the
best documentation is hand-written, which means that just by writing _any_
documentation, you are repeating yourself. Sure,
[documentation generators](http://en.wikipedia.org/wiki/Comparison_of_documentation_generators)
exist and are useful, but it’s important to acknowledge that they still require
input from humans to function.

The pursuit of _minimizing_ repetition remains valiant! ARID does not mean
[WET](https://en.wikipedia.org/wiki/Don't_repeat_yourself#DRY_vs_WET_solutions),
hence the word choice. It means: try to keep things _as DRY as possible_ but
also recognize that you’ll inevitably need some amount of “moisture” to produce
documentation.

Cultivating an awareness of this inconvenient truth will hopefully be a helpful
step toward reminding developers that a need often exists to update
documentation along with code.

### Skimmable

_Structure content to help readers identify and skip over concepts which they
already understand or are not relevant to their immediate questions._

Burying concepts in prose and verbiage demands more time from readers seeking
answers to specific questions. Save your readers’ time by writing like a
newspaper instead of a novel.

Specifically:

- Headings — should be descriptive and concise.
- Hyperlinks — should surround words that describe the link itself (and never
  phrases like “click here” or “this page”).
- Paragraphs and list items — should begin with identifiable concepts as early
  as possible.

### Exemplary

_Include (some) examples and tutorials in content._

Many readers look first towards examples for quick answers, so including them
will help save these people time. Try to write examples for the most common use
cases, but not for everything. Too many examples can make the documentation
less. Also, consider separating examples and tutorials from more dense reference
information to further help readers skim.

### Consistent

_Use consistent language and formatting in content._

The more content editors you have, the more important a
[style guide](https://www.writethedocs.org/guide/writing/style-guides/) becomes
in facilitating consistency. Consistency also helps make documentation and.

### Current

_Consider incorrect documentation to be worse than missing documentation._

When software changes faster than its documentation, the users suffer. Keep it
up to date.

Make every effort to write content that is version-agnostic and thus in less
need of maintenance. For example, generalize version numbers of software when
they occur in tutorials (such as extracting a source code tarball with the
version number in the file name).

Some users will remain on older versions of your software, and thus require
older versions of your documentation. Proper documentation platforms will
accommodate such needs gracefully.

## Principles for content sources

_A “source” refers to a system used to store and edit content. Examples of
sources include: text files written using reStructuredText or Markdown, HTML
content in a CMS database, help text stored within strings in application code,
code comments to be assembled later into formalized documentation, and others
too._

All **sources** should be…

### Nearby

_Store sources as close as possible to the code which they document._

Give developers systems that allow them to easily make documentation changes
along with their code changes. One way is to store documentation content in
comment blocks within application source code. Another is to store it in
separate text files but within the same repository as the application’s source
code. Either way, the goal is to merge (as much as possible) the workflows for
development and documentation.

### Unique

_Eliminate content overlap between separate sources._

Storing content in different sources is okay, as long as the scope of each
source is clearly defined and disjoint with other sources. The goal here is to
prevent any parallel maintenance (or worse — _lack_ of maintenance) of the same
information across multiple sources.

## Principles for publications

_A “publication” refers to a single, cohesive tool that readers use to consume
documentation. It may be static or interactive — digital or paper. Multiple
publications may be created from a single source (such as web and PDF versions
of the same manual). Although rarer, multiple sources may be used to create a
single publication. More examples of publications include: API reference, man
page, command line_ `--help` _output, in-application help tips, online
tutorials, internal engineering manuals, and others too._

Each **publication** should be…

### Discoverable

_Funnel users intuitively towards publications through all likely pathways._

Try to identify everywhere the user might go looking for documentation, and in
all of those places, insert helpful pointers for them to find it. Documentation
need not _exist_ in all of these places, just pointers to it.

If a user manual is published in the woods, and no one is around to read it,
does it exist? [Discoverability](https://en.wikipedia.org/wiki/Discoverability)
says “no”.

### Addressable

_Provide addresses to readers that link directly to content at a granular
level._

The ability to reference _specific_ sections deep within a body of documentation
facilitates productive communication about the documentation, even with one’s
self. These addresses can take the form of URLs, page numbers, or other forms
depending on the publication medium. Readers may wish to bookmark certain
sections, share them with other users, or provide feedback to the authors. The
more granular this ability, and the easier it is to access, the better.

### Cumulative

_Content should be ordered to cover prerequisite concepts first._

Can a reader follow your entire body of documentation, linearly, from start to
finish without getting confused? If so, the documentation is perfectly
“cumulative”, which is great, but not always possible. It’s something to strive
for, especially in tutorials and examples. If you have separated your tutorials
and examples from the reference documentation, then put the tutorials and
examples first. Then, content within the reference information section may be
ordered alphabetically or topically without regard to prerequisite needs.

The goal of cumulative ordering is not to encourage readers to consume your
documentation linearly — rather it is to help them narrow their search for
information when filling in gaps in their knowledge. If a reader arrives with
_some_ knowledge of the software and begins reading the documentation at the 25%
mark, they are likely to “rewind” when confused.

### Complete

_Within each publication, cover concepts in full, or not at all._

Picture some documentation of software like a map of a neighborhood. If the map
displays roads, readers will expect it to display _all_ roads (which exist and
are of the same _type_ being displayed). Perhaps the map does not display
_railroads_, for example. Thus, a reader approaching the map to look for
railroads will find zero and then seek a different map — but the map is still
“complete”, even with this shortcoming. “Complete” does not mean that the map
must describe _all_ characteristics of the land. It means simply that, for the
characteristics it chooses to describe, it should describe _all_ of them. A map
that displays fifty out of one hundred fire hydrants in a neighborhood is
_worse_ than a map that displays none.

As a good example, `iconv` is a command line tool for working with character
encodings. Its [man page](http://man7.org/linux/man-pages/man1/iconv.1.html)
covers _all_ of its available options but _none_ of the possible character
encodings accepted as values to these options. Instead, the man page instructs
the user to run `iconv -l` to produce a list of character encodings. In this
example, the man page and the list are separate publications, both of which are
complete, which is good!

Publishing partially completed documentation must be done cautiously. To avoid
misleading readers, make every effort to clearly state, up front, that a
particular concept is only covered partially.

### Beautiful

_Visual style should be intentional and aesthetically pleasing._

Aesthetics don’t matter to everyone — but (consciously or not) some readers will
struggle to find comfort in documentation that lacks attention to visual style.
Even in text-only documentation such as `--help` output, visual style is still
present in the form of spacing and capitalization. If visual style is not
important to you personally, then consider soliciting stylistic improvements
from others for whom it is.

## Principles for the body of publications

_A “body” refers to the collection of all the publications within a software
project and any of its sub-projects_

A documentation **body** should be…

### Comprehensive

_Ensure that together, all the publications in the body of documentation can
answer all questions the user is likely to have._

We can never create enough documentation to satisfy _all_ questions, however
obscure, that might arise from users — but satisfying the _likely_ questions is
certainly attainable and thus should be the goal of a body of documentation.
“Likely” is admittedly a blurry term, but it’s also relative, which means that a
body of documentation which answers very unlikely questions while failing to
answer likely ones is somewhat out of balance.

Answering some questions may require the user to read multiple publications,
which is okay.
