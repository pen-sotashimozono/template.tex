"""Shared drawing helpers for the Python figure pages under figures/src/.

Not a page itself: it lives with build.sh in .github/tools/figures/, which puts
this directory on PYTHONPATH, so a page script can `import schematic`. A page
is a script that writes one SVG to the path it is given:

    import sys
    from schematic import ELE, head, label, arrow

    s = head()
    s.append(label(40, 60, "r", "1", bold=True, italic=False))
    s.append("</svg>")
    open(sys.argv[1], "w").write("\\n".join(s))

The SVG carries only a viewBox, so the slide or document sizes it. Labels are
math-style (serif italic base, upright subscript) so a picture can sit next to
the equations that come from preamble.tex; the colours are the ones defined
there (\\definecolor{nuc}, {ele}), so pictures and equations agree.
"""

import math

NUC, ELE, LINE, INK = "#c96a1b", "#2e6fba", "#777", "#222"   # nucleus, electron, guide line, text
W, H = 480, 360                                              # default canvas


def label(x, y, base, sub="", color=INK, bold=False, italic=True, extra="", sub_italic=False):
    """A math-style label: serif italic base, subscript (upright unless an index), optional tail."""
    style = 'font-style="italic"' if italic else ""
    weight = 'font-weight="bold"' if bold else ""
    sub_style = "italic" if sub_italic else "normal"
    sub_span = (f'<tspan font-size="14" font-style="{sub_style}" font-weight="normal" dy="5">{sub}</tspan>'
                if sub else "")
    tail = f'<tspan dy="{-5 if sub else 0}">{extra}</tspan>' if extra else ""
    return (f'<text x="{x}" y="{y}" font-size="21" fill="{color}" {style} {weight}>'
            f"{base}{sub_span}{tail}</text>")


def hat(x, y, sym, sub, color=INK):
    """An operator label with a circumflex (T-hat, V-hat), the hat drawn as a path so every font agrees."""
    return (f'<path d="M{x+3},{y-17} L{x+8},{y-22} L{x+13},{y-17}" fill="none" '
            f'stroke="{color}" stroke-width="1.4"/>' + label(x, y, sym, sub, color))


def nucleus(x, y, r=17):
    """A positive charge: a filled disc with a plus."""
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{NUC}"/>'
            f'<text x="{x}" y="{y+6}" text-anchor="middle" font-size="20" '
            f'fill="white" font-weight="bold">+</text>')


def particle(x, y, r=6, color=ELE):
    """A point particle (an electron by default)."""
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'


def arrow(x, y, ang, length, r0, color, marker, width):
    """An arrow leaving a point at angle `ang` (degrees), starting r0 from it; `marker` from head()."""
    a = math.radians(ang)
    x0, y0 = x + r0 * math.cos(a), y + r0 * math.sin(a)
    x1, y1 = x + (r0 + length) * math.cos(a), y + (r0 + length) * math.sin(a)
    return (f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" '
            f'stroke="{color}" stroke-width="{width}" marker-end="url(#{marker})"/>')


def coulomb(p, q):
    """A dashed interaction line between two points."""
    return (f'<line x1="{p[0]}" y1="{p[1]}" x2="{q[0]}" y2="{q[1]}" stroke="{LINE}" '
            f'stroke-width="1.4" stroke-dasharray="5 4"/>')


def head(extra_defs="", w=W, h=H):
    """The opening of an SVG with arrow markers `an` (nucleus colour) and `ae` (electron colour)."""
    def marker(name, color):
        return (f'<marker id="{name}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" '
                f'markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10z" fill="{color}"/></marker>')
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f"font-family=\"'STIX Two Text','Times New Roman',serif\">",
            "<defs>", marker("an", NUC), marker("ae", ELE), extra_defs, "</defs>",
            f'<rect width="{w}" height="{h}" fill="white"/>']
