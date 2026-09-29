"""example, page 03: a Python drawing page -- two nuclei, two electrons and the
dashed interactions between them, built from schematic.py's helpers. A page is a
script that writes one SVG to the path it is given (build.sh passes it)."""
import sys

from schematic import coulomb, head, label, nucleus, particle

A, B, e1, e2 = (140, 190), (340, 190), (100, 80), (380, 90)
s = head()
s += [coulomb(p, q) for p, q in ((e1, A), (e1, B), (e2, A), (e2, B), (e1, e2))]
s += [nucleus(*A), nucleus(*B), particle(*e1, r=7), particle(*e2, r=7)]
s += [label(e1[0] - 22, e1[1] - 8, "1", italic=False), label(e2[0] + 12, e2[1] - 8, "2", italic=False),
      label(226, 70, "r", "12")]
s.append("</svg>")
with open(sys.argv[1], "w") as f:
    f.write("\n".join(s).replace('viewBox="0 0 480 360"', 'viewBox="40 30 400 215"', 1))
