#!/usr/bin/env python3
"""Convert a pptx / docx to PDF through LibreOffice's UNO API (python3-uno).

For a pptx, LibreOffice's automatic gap between Asian and Latin text is turned
off first: PowerPoint adds none, so the gap widens every mixed line. Word does
add it, so a docx is converted as is.

    python3 .github/scripts/soffice_pdf.py <source> <pdf>
"""
import os
import subprocess
import sys
import tempfile
import time

import uno
from com.sun.star.beans import PropertyValue


def prop(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


def texts(shape):
    """Every text-bearing object in a shape: itself, group members, table cells."""
    if shape.supportsService("com.sun.star.drawing.GroupShape"):
        for i in range(shape.getCount()):
            yield from texts(shape.getByIndex(i))
    elif shape.supportsService("com.sun.star.drawing.TableShape"):
        model = shape.Model
        for r in range(model.Rows.Count):
            for c in range(model.Columns.Count):
                yield model.getCellByPosition(c, r)
    elif hasattr(shape, "Text"):
        yield shape


def no_asian_gap(doc):
    pages = [doc.DrawPages.getByIndex(i) for i in range(doc.DrawPages.Count)]
    pages += [doc.MasterPages.getByIndex(i) for i in range(doc.MasterPages.Count)]
    for page in pages:
        for i in range(page.Count):
            for text in texts(page.getByIndex(i)):
                paras = text.Text.createEnumeration()
                while paras.hasMoreElements():
                    para = paras.nextElement()
                    if para.getPropertySetInfo().hasPropertyByName("ParaIsCharacterDistance"):
                        para.ParaIsCharacterDistance = False


def connect(port):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(120):
        try:
            return resolver.resolve(
                f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext")
        except Exception:
            time.sleep(0.5)
    sys.exit("soffice did not come up")


def main(source, pdf):
    source, pdf = os.path.abspath(source), os.path.abspath(pdf)
    port = 20000 + os.getpid() % 10000
    with tempfile.TemporaryDirectory() as profile:
        office = subprocess.Popen([
            "soffice", "--headless", "--invisible", "--norestore",
            f"-env:UserInstallation={uno.systemPathToFileUrl(profile)}",
            f"--accept=socket,host=127.0.0.1,port={port};urp;"])
        try:
            ctx = connect(port)
            desktop = ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", ctx)
            doc = desktop.loadComponentFromURL(
                uno.systemPathToFileUrl(source), "_blank", 0, (prop("Hidden", True),))
            if source.lower().endswith(".pptx"):
                no_asian_gap(doc)
                pdf_filter = "impress_pdf_Export"
            else:
                pdf_filter = "writer_pdf_Export"
            doc.storeToURL(uno.systemPathToFileUrl(pdf), (prop("FilterName", pdf_filter),))
            doc.close(True)
            try:
                desktop.terminate()
            except Exception:
                pass  # the bridge drops as soffice exits
            office.wait(timeout=60)
        finally:
            if office.poll() is None:
                office.kill()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
