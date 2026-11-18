#!/usr/bin/env python3
"""Build the PDF directly from the files in book/.

Pipeline: book/ -> build/book.md -> pandoc -> LaTeX -> lualatex (twice, for
page references). Everything generated goes to build/.

Usage:
    python3 tools/build.py           # assemble and typeset
    python3 tools/build.py --check   # only verify the toolchain
"""

import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
INPUT = os.path.join(BUILD, "book.md")
TEX = os.path.join(BUILD, "book.tex")
HEADER = os.path.join(BUILD, "header.tex")
PDF = os.path.join(BUILD, "book.pdf")
OUTPUT = os.path.join(ROOT, "Software Design & Craftsmanship.pdf")

PACKAGES = [
    "fontspec.sty", "booktabs.sty", "titlesec.sty", "fvextra.sty",
    "fancyvrb.sty", "xcolor.sty", "microtype.sty", "enumitem.sty",
    "hyperref.sty", "geometry.sty", "longtable.sty",
]
FONTS = ["Noto Serif", "DejaVu Sans", "DejaVu Sans Mono"]

PART_STARTS = {
    0: "Part I — Foundations of Design",
    3: "Part II — Designing Modules",
    9: "Part III — Constructing Code",
    15: "Part IV — Verification and Evolution",
    20: "Part V — Projects and People",
    24: "Part VI — Judgment",
}

PANDOC_OPTIONS = [
    "--top-level-division=chapter",
    "--metadata", "lang=en",
    "--include-in-header", HEADER,
    "--lua-filter", os.path.join(ROOT, "tools", "tables.lua"),
    "-V", "documentclass=book",
    "-V", "classoption=openany",
    "-V", "fontsize=10pt",
    "-V", "papersize=a4",
    "-V", "geometry:margin=2.3cm",
    "-V", "geometry:top=2.7cm",
    "-V", "geometry:bottom=2.9cm",
    "-V", "mainfont=Noto Serif",
    "-V", "sansfont=DejaVu Sans",
    "-V", "monofont=DejaVu Sans Mono",
    "-V", "colorlinks=true",
    "-V", "linkcolor=black",
    "-V", "urlcolor=Maroon",
    "-V", "toccolor=black",
]

HEADER_TEX = r"""
\setcounter{secnumdepth}{-1}
\usepackage{graphicx}
\graphicspath{{../}{./}}
\setkeys{Gin}{width=0.85\linewidth,height=0.62\textheight,keepaspectratio}
\usepackage{fvextra}
\fvset{breaklines=true,breakanywhere=true,fontsize=\footnotesize}
\DefineVerbatimEnvironment{Highlighting}{Verbatim}{breaklines=true,breakanywhere=true,commandchars=\\\{\}}
\setlength{\emergencystretch}{6em}
\tolerance=2000
\renewcommand{\arraystretch}{1.15}
\setlength{\extrarowheight}{1.6pt}
\makeatletter
% Keep the roman/arabic split but do not insert the blank verso page that
% \cleardoublepage would add after the contents.
\renewcommand{\mainmatter}{\clearpage\@mainmattertrue\pagenumbering{arabic}}
\renewcommand{\maketitle}{%
  \begin{titlepage}%
  \centering
  \vspace*{5.5cm}
  {\sffamily\bfseries\fontsize{28}{34}\selectfont \@title\par}
  \vspace{0.9cm}
  {\sffamily\large Design, construction, and judgment in practice\par}
  \vfill
  \end{titlepage}%
  \setcounter{footnote}{0}%
}
\makeatother
\usepackage{titlesec}
\titleformat{\chapter}[block]{\normalfont\sffamily\Huge\bfseries\raggedright\hyphenpenalty=10000\exhyphenpenalty=10000}{}{0pt}{}
\titlespacing*{\chapter}{0pt}{10pt}{34pt}
\titleformat{\section}{\normalfont\sffamily\Large\bfseries\raggedright\hyphenpenalty=10000}{}{0pt}{}
\titlespacing*{\section}{0pt}{18pt}{8pt}
"""

INSTALL_HINT = """\
Install the typesetting dependencies, then run the build again.

  Arch:    sudo pacman -S pandoc texlive-latexextra texlive-fontsrecommended \\
                            ttf-dejavu noto-fonts
  Debian:  sudo apt install pandoc texlive-luatex texlive-latex-extra \\
                            texlive-fonts-recommended fonts-dejavu-core fonts-noto-core
  macOS:   brew install pandoc; brew install --cask mactex-no-gui
"""


def missing_packages():
    out = []
    for package in PACKAGES:
        found = subprocess.run(["kpsewhich", package], capture_output=True,
                               text=True)
        if not found.stdout.strip():
            out.append(package)
    return out


def missing_fonts():
    listed = subprocess.run(["fc-list", ":", "family"], capture_output=True,
                            text=True).stdout
    out = []
    for font in FONTS:
        if not re.search(r"(?m)^%s(,|$)" % re.escape(font), listed):
            out.append(font)
    return out


def pandoc_version():
    try:
        raw = subprocess.run(["pandoc", "--version"], capture_output=True,
                             text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    match = re.search(r"pandoc(?:-server)?\s+(\d+)\.(\d+)", raw)
    return (int(match.group(1)), int(match.group(2))) if match else None


def preflight():
    problems = []
    for tool in ("pandoc", "kpsewhich", "fc-list", "lualatex"):
        if shutil.which(tool) is None:
            problems.append("missing program: %s" % tool)
    version = pandoc_version()
    if version is not None and version < (3, 0):
        problems.append("pandoc %d.%d is too old; version 3.0 or later is required"
                        % version)
    if problems:
        print("\n".join(problems) + "\n\n" + INSTALL_HINT, file=sys.stderr)
        return False
    packages = missing_packages()
    if packages:
        problems.append("missing LaTeX packages: " + ", ".join(packages))
    fonts = missing_fonts()
    if fonts:
        problems.append("missing fonts: " + ", ".join(fonts))
    if problems:
        print("\n".join(problems) + "\n\n" + INSTALL_HINT, file=sys.stderr)
        return False
    print("toolchain ok: pandoc, lualatex, packages, fonts")
    return True


def read(path):
    with open(os.path.join(ROOT, "book", path), encoding="utf-8") as handle:
        return handle.read().strip()


def assemble_markdown():
    """Concatenate the front matter, contents, and chapters in reading order."""
    chapters = sorted(
        name for name in os.listdir(os.path.join(ROOT, "book"))
        if re.match(r"\d\d_.*\.md$", name) and not name.startswith("00_")
    )

    body = []
    for index, name in enumerate(chapters):
        if index in PART_STARTS:
            body.append("# %s" % PART_STARTS[index])
        body.append(read(name))

    return (
        "---\n"
        'title: "Software Design & Craftsmanship"\n'
        "lang: en\n"
        "---\n\n"
        + read("00_front_matter.md") + "\n\n"
        + read("table_of_contents.md") + "\n\n"
        + "\n\n".join(body) + "\n"
    )


def convert(markdown):
    """Rewrite book markup that LaTeX needs expressed differently."""
    # Keep the YAML metadata block out of the structural cleanup below.
    match = re.match(r"^(---\n.*?\n---\n)(.*)$", markdown, re.S)
    metadata, body = match.group(1), match.group(2)

    # Parts become unnumbered LaTeX \part commands.
    def part(match):
        return "```{=latex}\n\\part{" + match.group(2).strip() + "}\n```"

    body = re.sub(r"^# (Part [IVX]+) — (.+)$", part, body, flags=re.M)

    # Horizontal rules are structural artefacts, not content.
    body = re.sub(r"^---\s*$", "", body, flags=re.M)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    return metadata + body + "\n"


def make_spaces_breakable(tex):
    """Allow line breaks at the spaces inside inline code spans.

    Pandoc writes `\\texttt{a\\ b}` with a control space, which LaTeX cannot
    break. A long code span then overflows a narrow table cell. Inside
    \\texttt a plain space is set in the same monospace font, so replacing the
    control space with a normal space only makes the text wrappable.
    """
    out = []
    index = 0
    marker = "\\texttt{"
    while True:
        start = tex.find(marker, index)
        if start == -1:
            out.append(tex[index:])
            break
        out.append(tex[index:start + len(marker)])
        pos = start + len(marker)
        depth = 1
        chunk = []
        while pos < len(tex) and depth > 0:
            char = tex[pos]
            if char == "\\" and pos + 1 < len(tex) and tex[pos + 1] in "{}":
                # An escaped brace is a literal character, not a delimiter.
                chunk.append(tex[pos:pos + 2])
                pos += 2
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    break
            chunk.append(char)
            pos += 1
        out.append("".join(chunk).replace("\\ ", " ") + "}")
        index = pos + 1
    return "".join(out)


def run(command, **kwargs):
    return subprocess.call(command, **kwargs)


def main(argv):
    if "--check" in argv:
        return 0 if preflight() else 1
    if not preflight():
        return 1

    os.makedirs(BUILD, exist_ok=True)
    markdown = convert(assemble_markdown())
    with open(INPUT, "w", encoding="utf-8") as handle:
        handle.write(markdown)
    words = len(re.findall(r"\b[\w'-]+\b", markdown))
    print("book assembled: 25 chapters, %d words" % words)
    with open(HEADER, "w", encoding="utf-8") as handle:
        handle.write(HEADER_TEX)

    highlight = ("--syntax-highlighting=tango"
                 if pandoc_version() >= (3, 6) else "--highlight-style=tango")
    status = run(["pandoc", INPUT, "-s", "-o", TEX, highlight]
                 + PANDOC_OPTIONS, cwd=ROOT)
    if status != 0:
        return status

    with open(TEX, encoding="utf-8") as handle:
        tex = handle.read()
    with open(TEX, "w", encoding="utf-8") as handle:
        handle.write(make_spaces_breakable(tex))

    command = ["lualatex", "-interaction=nonstopmode", "-halt-on-error",
               "book.tex"]
    for _ in range(2):
        status = run(command, cwd=BUILD, stdout=subprocess.DEVNULL)
        if status != 0:
            print("lualatex failed; see build/book.log", file=sys.stderr)
            return status

    overfull = 0
    log = os.path.join(BUILD, "book.log")
    if os.path.exists(log):
        with open(log, encoding="utf-8", errors="replace") as handle:
            overfull = handle.read().count("Overfull \\hbox")

    shutil.copyfile(PDF, OUTPUT)
    print("wrote %s (%d overfull lines)" % (OUTPUT, overfull))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
