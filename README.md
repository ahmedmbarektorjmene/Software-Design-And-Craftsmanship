# Software Design & Craftsmanship

*A working programmer's guide to design, construction, and judgment.*

This book is about the part of programming that a language reference cannot
teach: how to decide what a system should look like, how to keep it
understandable as it grows, and how to work in a way that leaves the code
better than you found it.

---

## Why this book exists

Most of what determines whether software survives is invisible in a
repository: the shape of a module boundary, the name of a function, the
decision not to add an abstraction, the comment that explains *why*. These
decisions are made thousands of times per project, usually under time
pressure, and they compound. A codebase that is easy to change after five
years is the accumulated result of small, deliberate choices.

The available advice is scattered and often contradictory. One camp says
design up front; another says let the design emerge. One says comment
everything; another says make the code self-documenting. Both camps are
right — under different conditions. This book puts those positions side by
side, explains the forces behind each, and helps you decide which applies to
the problem in front of you.

It does not offer rules to follow blindly. Rules break at the edges, and most
of the interesting work happens at the edges. It offers understanding of the
forces, worked examples, and practice.

## Who it is for

- **Working programmers** who can write code but want to get better at
  deciding what code to write.
- **Senior developers and tech leads** who review designs, mentor others,
  and need vocabulary for the trade-offs they already sense.
- **Students and career changers** who have learned a language and want the
  professional craft that comes after it.

The book assumes fluency in at least one modern language. All examples are
TypeScript, chosen because its type system can express design intent —
unions, readonly data, exhaustive checks — without hiding runtime behaviour.
Readers who work in another typed language will have no trouble following
along; readers who work in a dynamically typed language will find the ideas
transfer directly and the type annotations easy to read.

## What is inside

Twenty-five chapters in six parts:

| Part | Subject | Chapters |
|------|---------|----------|
| I | Foundations of design: craftsmanship, complexity, strategic investment | 1–3 |
| II | Designing modules: boundaries, information hiding, interfaces, errors | 4–9 |
| III | Constructing code: naming, comments, routines, control flow, data, layout | 10–15 |
| IV | Verification and evolution: testing, debugging, refactoring, performance, concurrency | 16–20 |
| V | Projects and people: requirements, estimation, tooling, teams, practice | 21–24 |
| VI | Judgment: a field guide, including where experts disagree | 25 |

Every chapter opens with a scenario, states its learning objectives, develops
one subject, and ends with a summary and exercises. The exercises are the
point: reading about design changes what you notice, doing the exercises
changes what you can do.

A suggested reading order for different backgrounds is in the front matter of
the book.

## Reading the book

- [`book/`](book) — the book's source: front matter, contents, and one
  Markdown file per chapter.
- `Software Design & Craftsmanship.pdf` — the typeset edition, produced by
  the build.

The PDF is built directly from the files in `book/`; there is no intermediate
assembled manuscript to keep in sync.

## Building the PDF

### Requirements

- [pandoc](https://pandoc.org/) 3.0 or later (Debian and Ubuntu still ship
  2.x; install the `.deb` from the pandoc release page if `just doctor`
  reports an old version)
- LuaLaTeX with a few standard packages (`texlive-luatex`,
  `texlive-latex-extra`, `texlive-fonts-recommended` on Debian;
  `texlive-luatex` + `texlive-latexextra` on Arch)
- The fonts **Noto Serif**, **DejaVu Sans**, and **DejaVu Sans Mono**
- Python 3 (standard library only)
- [just](https://github.com/casey/just) (optional; the Python scripts run
  directly)

Install on Arch:

```sh
sudo pacman -S pandoc texlive-luatex texlive-latexextra \
               texlive-fontsrecommended ttf-dejavu noto-fonts
```

Install on Debian/Ubuntu:

```sh
sudo apt install pandoc texlive-luatex texlive-latex-extra \
                 texlive-fonts-recommended fonts-dejavu-core fonts-noto-core
```

Install on macOS:

```sh
brew install pandoc
brew install --cask mactex-no-gui
```

### One command

```sh
just
```

This reads the files in `book/`, converts them to LaTeX, and typesets
`Software Design & Craftsmanship.pdf` with LuaLaTeX. Intermediate files go
to `build/`.

Useful variants:

```sh
just doctor   # report missing tools, packages, or fonts
just check    # type-check every TypeScript example
just clean    # remove build/
```

`just` is a small command runner; install it with `cargo install just` or
your package manager. The scripts are plain Python, so `python3 tools/build.py`
does the same thing if you would rather not install it.

## Type-checking the examples

Every TypeScript example is a self-contained module that compiles under
`strict` with TypeScript 5.9 or later. To verify them:

```sh
npm install
just check
```

The checker extracts each fenced `ts` block, compiles it in isolation, and
reports any diagnostic against the chapter and block number. Continuous
integration runs the same check on every push.

## Repository layout

```
book/                  front matter, contents, and one file per chapter
assets/                figures, flat and named for what they show
tools/
  build.py             book/ -> PDF (pandoc + LuaLaTeX)
  check_code.py        TypeScript example checker
  tables.lua           content-aware table column widths
.github/workflows/     CI: build the PDF, type-check the examples
```

## Figures

Figures live in `assets/` and are referenced from the chapter files. Each
file is named for what it shows, so replacing an illustration only requires
overwriting the file with the same name.

## Contributing

Corrections, clarifications, and better examples are welcome. Please open an
issue describing the problem, or a pull request that changes one chapter and
keeps the prose style consistent with its neighbours. Run `just` and
`just check` before submitting.

## License

Released under the MIT License; see [`LICENSE`](LICENSE). You may use,
copy, modify, and distribute the text and the examples, with attribution.
