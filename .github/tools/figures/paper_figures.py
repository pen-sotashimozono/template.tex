#!/usr/bin/env python3
"""A cited paper's own figures as SVG: figures/papers/<bibkey>-fig<N>.svg.

    python3 .github/tools/figures/paper_figures.py <bibkey>              # all figures, from the arXiv source
    python3 .github/tools/figures/paper_figures.py <bibkey> 1 4          # only Figs. 1 and 4
    python3 .github/tools/figures/paper_figures.py <bibkey> crop <N> <page> <x> <y> <w> <h>
                                                                   # figure N cropped from papers/<bibkey>.pdf

From the arXiv e-print: the main .tex (with its \\input files inlined) is read
in order, and figure environments are numbered as the paper numbers them, so
<bibkey>-fig3.svg is the paper's Fig. 3. A figure made of several files gets
fig3a, fig3b, ... in the order they are included. Vector files (pdf, eps) are
converted with pdftocairo (eps through epstopdf); raster files (png, jpg) are
embedded unchanged in an SVG wrapper. Each SVG carries the figure's label and
caption in its <desc>, so nothing but the SVGs is kept. Given figure numbers,
only those are written (and only those replaced); without, every figure is,
and the key's old SVGs are removed first.

Without an arXiv source (old or publisher-only papers), crop the figure from
the local PDF as vector: <page> is 1-based, x y w h in PDF points from the
page's top-left -- read them off `pdftocairo -png -r 72` of that page, where
one pixel is one point.

The arXiv id is the entry's `eprint`, or `doiget link <doi>` when there is none.
These are the authors' figures: cite the paper wherever one is shown.
"""
import base64
import html
import io
import pathlib
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "figures" / "papers"
EXTS = (".pdf", ".eps", ".png", ".jpg", ".jpeg")


def entry(key):
    rows = subprocess.run(["awk", "-f", ".github/scripts/bibentries.awk", "references.bib"],
                          cwd=ROOT, capture_output=True, text=True, check=True).stdout
    for line in rows.splitlines():
        k, ep, doi = line.rstrip("\r").split("\t")
        if k == key:
            return ep, doi
    sys.exit(f"no bib entry {key}")


def arxiv_id(key):
    ep, doi = entry(key)
    if ep != "-":
        return ep
    if doi != "-":
        r = subprocess.run(["doiget", "link", doi, "--mode", "json"], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL)
        m = re.search(r'"arxiv":\s*"([^"]+)"', r.stdout)
        if m:
            return m.group(1)
    sys.exit(f"{key}: no arXiv source; crop from papers/{key}.pdf instead (see --help)")


def with_desc(svg: str, desc: str) -> str:
    """Put the caption into the SVG, right after the opening <svg ...> tag."""
    tag = f"<desc>{html.escape(desc)}</desc>"
    return re.sub(r"(<svg\b[^>]*>)", lambda m: m.group(1) + tag, svg, count=1)


def to_svg(src: pathlib.Path, dst: pathlib.Path, desc: str):
    ext = src.suffix.lower()
    if ext == ".eps":
        pdf = src.with_suffix(".conv.pdf")
        subprocess.run(["epstopdf", str(src), "-o", str(pdf)], check=True, capture_output=True)
        src, ext = pdf, ".pdf"
    if ext == ".pdf":
        subprocess.run(["pdftocairo", "-svg", "-f", "1", "-l", "1", str(src), str(dst)],
                       check=True, capture_output=True)
        dst.write_text(with_desc(dst.read_text(), desc))
        return
    from PIL import Image
    w, h = Image.open(src).size
    mime = "image/png" if ext == ".png" else "image/jpeg"
    data = base64.b64encode(src.read_bytes()).decode()
    dst.write_text(with_desc(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        f'<image width="{w}" height="{h}" xlink:href="data:{mime};base64,{data}"/></svg>\n', desc))


def inline(tex: pathlib.Path, base: pathlib.Path, seen=None) -> str:
    """The main file with its \\input / \\include files pasted in, in reading order."""
    seen = seen or set()
    s = re.sub(r"(?<!\\)%.*", "", tex.read_text(errors="replace"))

    def sub(m):
        name = m.group(1).strip()
        for cand in (base / name, base / (name + ".tex")):
            if cand.is_file() and cand not in seen:
                seen.add(cand)
                return inline(cand, base, seen)
        return ""
    return re.sub(r"\\(?:input|include)\{([^}]*)\}", sub, s)


def resolve(base: pathlib.Path, name: str, gpaths):
    for d in [base] + gpaths:
        p = d / name
        if p.suffix.lower() in EXTS and p.is_file():
            return p
        for e in EXTS:
            if p.with_name(p.name + e).is_file():
                return p.with_name(p.name + e)
    return None


def from_arxiv(key, only=()):
    aid = arxiv_id(key)
    req = urllib.request.Request(f"https://arxiv.org/e-print/{aid}",
                                 headers={"User-Agent": "doiget-refs/1 (paper figures)"})
    raw = urllib.request.urlopen(req, timeout=300).read()
    with tempfile.TemporaryDirectory() as t:
        base = pathlib.Path(t)
        try:
            tarfile.open(fileobj=io.BytesIO(raw)).extractall(base, filter="data")
        except tarfile.ReadError:
            sys.exit(f"{key}: arXiv:{aid} is a single-file submission, no figure files")
        mains = [p for p in base.rglob("*.tex") if "\\documentclass" in p.read_text(errors="replace")]
        if not mains:
            sys.exit(f"{key}: no main .tex in arXiv:{aid}")
        main = max(mains, key=lambda p: p.stat().st_size)
        s = inline(main, main.parent)
        gpaths = [main.parent / g for g in re.findall(r"\{([^{}]+)\}", " ".join(
            re.findall(r"\\graphicspath\{((?:\{[^}]*\})+)\}", s)))]
        OUT.mkdir(parents=True, exist_ok=True)
        if not only:
            for old in OUT.glob(f"{key}-fig*.svg"):
                old.unlink()
        figs = re.findall(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", s, re.S)
        made = []
        missing = [n for n in only if not 1 <= n <= len(figs)]
        if missing:
            sys.exit(f"{key}: the source has {len(figs)} figures; no Fig. {missing}")
        for n, body in enumerate(figs, 1):
            if only and n not in only:
                continue
            for old in OUT.glob(f"{key}-fig{n}.svg"):
                old.unlink()
            for old in OUT.glob(f"{key}-fig{n}[a-z].svg"):
                old.unlink()
            files = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", body)
            label = ", ".join(re.findall(r"\\label\{([^}]*)\}", body))
            cap = re.search(r"\\caption(?:\[[^\]]*\])?\{(.*)", body, re.S)
            cap = re.sub(r"\s+", " ", cap.group(1)).strip() if cap else ""
            for i, f in enumerate(files):
                src = resolve(main.parent, f.strip(), gpaths)
                if src is None:
                    print(f"  fig{n}: {f} not in the source", file=sys.stderr)
                    continue
                name = f"{key}-fig{n}" + (chr(ord("a") + i) if len(files) > 1 else "")
                desc = f"{key}, arXiv:{aid}, Fig. {n}" + (f" ({label})" if label else "") + f": {cap}"
                to_svg(src, OUT / f"{name}.svg", desc)
                made.append(name)
        print(f"{len(made)} figure file(s) from arXiv:{aid}: " + " ".join(made))


def crop(key, n, page, x, y, w, h):
    pdf = ROOT / "papers" / f"{key}.pdf"
    if not pdf.is_file():
        sys.exit(f"no {pdf}")
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{key}-fig{n}.svg"
    subprocess.run(["pdftocairo", "-svg", "-f", page, "-l", page, "-x", x, "-y", y, "-W", w, "-H", h,
                    "-paperw", w, "-paperh", h, str(pdf), str(dst)], check=True)
    dst.write_text(with_desc(dst.read_text(), f"{key}, Fig. {n}: cropped from papers/{key}.pdf p.{page}"))
    print(dst.relative_to(ROOT))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
    elif len(a) == 1 or all(x.isdigit() for x in a[1:]):
        from_arxiv(a[0], tuple(int(x) for x in a[1:]))
    elif a[1] == "crop" and len(a) == 8:
        crop(a[0], *a[2:])
    else:
        sys.exit(__doc__)
