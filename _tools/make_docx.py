# -*- coding: utf-8 -*-
"""Сборщик отчётов .docx (чистый Python: zipfile + OOXML, без внешних зависимостей).

Адаптация _tools/make_docx.py из репозитория kert25/6sem_internet_proga
под дисциплину «Интернет-программирование» 7-го семестра (препод. Сафронова М.А.).

Титульный лист — по образцу ЛР1.docx (Times New Roman 14 pt, A4,
поля 2/1,5/2/3 см, разрыв страницы, номер страницы в колонтитуле, скрытый на титуле).

Использование:
    py make_docx.py --out <ЛР2.docx> --num 2 --theme "Гиперссылки" --content content.json

content.json — список элементов:
    {"h":  "Заголовок раздела"}               — полужирный Times New Roman 14 pt
    {"p":  "текст"}                            — обычный абзац Times New Roman 16 pt
    {"code": "текст программы"}                — листинг Courier New 12 pt
    {"codefile": "путь/к/файлу"}               — листинг из файла (UTF-8)
    {"img": "путь.png", "caption": "Подпись"}  — рисунок по центру + подпись 12 pt
    {"pb": true}                               — разрыв страницы
Относительные пути в content.json разрешаются от каталога самого content.json.
"""
import sys, os, json, struct, zipfile, argparse

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"

TNR = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'
COURIER = '<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/>'

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

def run(text, font=TNR, sz=28, b=False, br_type=None):
    """Один run: sz в полукеглях (28 = 14 pt), b — полужирный, br_type — тип <w:br/>."""
    rpr = "<w:rPr>%s%s<w:sz w:val=\"%d\"/><w:szCs w:val=\"%d\"/></w:rPr>" % (
        font, "<w:b/>" if b else "", sz, sz)
    br = '<w:br w:type="%s"/>' % br_type if br_type else ""
    return "<w:r>%s%s<w:t xml:space=\"preserve\">%s</w:t></w:r>" % (rpr, br, esc(text))

def para(runs, jc=None, spacing=True, ind=None):
    """Абзац: runs — строка XML run'ов или их список."""
    body = "".join(runs) if isinstance(runs, list) else runs
    ppr = "<w:pPr>"
    if spacing:
        ppr += '<w:spacing w:before="120" w:after="120" w:line="240" w:lineRule="auto"/>'
    if ind:
        ppr += '<w:ind w:left="%d" w:right="%d"/>' % ind
    if jc:
        ppr += '<w:jc w:val="%s"/>' % jc
    ppr += "</w:pPr>"
    return "<w:p>%s%s</w:p>" % (ppr, body)

def title_page(num, theme):
    """Титульный лист — по образцу ЛР1.docx (7-й семестр, преп. Сафронова М.А.)."""
    p = []
    p.append(para(run("МИНОБРНАУКИ РОССИИ"), jc="center"))                      # P00
    p.append(para(run("Федеральное государственное бюджетное "), jc="center"))  # P01
    p.append(para([run("образовательное учреждение высшего образования"),        # P02
                   run("«Тульский государственный университет»", br_type="")], jc="center"))
    p.append(para(run("Институт прикладной математики и компьютерных наук"), jc="center"))  # P03
    p.append(para(run(""), jc="center"))   # P04
    p.append(para(run("")))                # P05
    p.append(para(run("")))                # P06
    p.append(para(run("")))                # P07
    p.append(para(run(""), jc="center"))   # P08
    p.append(para(run("ЛАБОРАТОРНАЯ РАБОТА №%d" % num), jc="center"))           # P09
    p.append(para(run("по дисциплине"), jc="center"))                            # P10
    p.append(para(run("Интернет-программирование"), jc="center", ind=(567, 566)))  # P11
    p.append(para(run(" "), jc="center", ind=(567, 566)))                        # P12
    p.append(para(run("по теме"), jc="center", ind=(567, 566)))                  # P13
    p.append('<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
             '<w:jc w:val="center"/></w:pPr>%s</w:p>' % run("«%s»" % theme))     # P14
    p.append(para(run(" ")))                # P15
    p.append(para(run(""), jc="center"))   # P16
    p.append(para(run(""), jc="center"))   # P17
    p.append(para(run(""), jc="center"))   # P18
    p.append(para([run("Выполнил: ст. гр.  220032-11" + " " * 52),               # P19
                   run("Лаукерт К.М. "), run(" ")], jc="both"))
    p.append(para(run(""), jc="both"))     # P20
    p.append(para([run("Принял: к.т.н., доцент ИПМКН" + " " * 44),              # P21
                   run("Сафронова М.А. "), run(" ")], jc="both"))
    for _ in range(6):                      # P22-P27
        p.append(para(run(""), jc="both"))
    p.append(para(run("Тула 2026"), jc="center"))                               # P28
    p.append('<w:p>%s</w:p>' % run("", br_type="page"))                          # P29
    return "".join(p)

def heading(text):
    return para(run(text, b=True))

def body_para(text):
    return para(run(text, sz=32))

def code_block(code):
    out = []
    for ln in code.rstrip("\n").split("\n"):
        out.append(para(run(ln if ln else " ", font=COURIER, sz=24)))
    return "".join(out)

def image_xml(png_path, rid, img_id):
    """Рисунок по центру + подпись. Возвращает (XML, данные PNG)."""
    with open(png_path, "rb") as f:
        data = f.read()
    wpx, hpx = struct.unpack(">II", data[16:24])
    maxw = int(16.5 / 2.54 * 96)  # ~16,5 см полезной ширины страницы
    if wpx > maxw:
        hpx = int(hpx * maxw / wpx)
        wpx = maxw
    emu_w, emu_h = wpx * 9525, hpx * 9525
    drawing = (
        '<w:r><w:drawing><wp:inline xmlns:wp="%(wp)s" distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="%(w)d" cy="%(h)d"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:docPr id="%(id)d" name="Рисунок %(id)d"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="%(a)s" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic xmlns:a="%(a)s"><a:graphicData uri="%(pic)s">'
        '<pic:pic xmlns:pic="%(pic)s"><pic:nvPicPr>'
        '<pic:cNvPr id="%(id)d" name="Рисунок %(id)d"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="%(rid)s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%(w)d" cy="%(h)d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
        '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'
    ) % {"wp": WP, "a": A, "pic": PIC, "w": emu_w, "h": emu_h, "id": img_id, "rid": rid}
    return drawing, data

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="png" ContentType="image/png"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
%s</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="%(w)s">
<w:docDefaults><w:rPrDefault><w:rPr>%(tnr)s<w:sz w:val="28"/><w:szCs w:val="28"/><w:lang w:val="ru-RU"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:before="120" w:after="120" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
</w:styles>"""

FOOTER = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
          '<w:ftr xmlns:w="%s">%s</w:ftr>') % (
    W,
    para('<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
         '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
         '<w:r><w:fldChar w:fldCharType="end"/></w:r>', jc="center"))

SECT_PR = ('<w:sectPr><w:footerReference w:type="default" r:id="rId2"/>'
           '<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="850" '
           'w:bottom="1134" w:left="1701" w:header="708" w:footer="708" w:gutter="0"/>'
           '<w:titlePg/></w:sectPr>')

def build(out, num, theme, content, workdir):
    def resolve(p):
        return os.path.normpath(os.path.join(workdir, p))
    paras = [title_page(num, theme)]
    # Шапка отчёта (вторая страница, как в образце)
    paras.append(para(run("Лабораторная работа №%d" % num, sz=32, b=True), jc="center"))
    paras.append(para(run("по теме «%s»" % theme, sz=32, b=True), jc="center"))
    paras.append(para(run(" ", sz=32)))
    media, img_rels = {}, []
    rid_n = 100
    for item in content:
        if "h" in item:
            paras.append(heading(item["h"]))
        elif "p" in item:
            paras.append(body_para(item["p"]))
        elif "codefile" in item:
            with open(resolve(item["codefile"]), encoding="utf-8") as f:
                paras.append(code_block(f.read()))
        elif "code" in item:
            paras.append(code_block(item["code"]))
        elif "img" in item:
            rid = "rIdImg%d" % rid_n
            drawing, data = image_xml(resolve(item["img"]), rid, rid_n)
            paras.append(para(drawing, jc="center"))
            if item.get("caption"):
                paras.append(para(run(item["caption"], sz=24), jc="center"))
            media["word/media/image%d.png" % rid_n] = data
            img_rels.append('<Relationship Id="%s" Type="http://schemas.openxmlformats.org'
                            '/officeDocument/2006/relationships/image" '
                            'Target="media/image%d.png"/>' % (rid, rid_n))
            rid_n += 1
        elif item.get("pb"):
            paras.append('<w:p>%s</w:p>' % run("", br_type="page"))
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<w:document xmlns:w="%s" xmlns:r="%s"><w:body>%s%s</w:body></w:document>'
                % (W, R, "".join(paras), SECT_PR))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", document)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS % "".join(img_rels))
        z.writestr("word/styles.xml", STYLES % {"w": W, "tnr": TNR})
        z.writestr("word/footer1.xml", FOOTER)
        for name, data in media.items():
            z.writestr(name, data)
    print("OK %s (%d байт, рисунков: %d)" % (out, os.path.getsize(out), len(media)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--num", type=int, required=True)
    ap.add_argument("--theme", required=True)
    ap.add_argument("--content", required=True, help="JSON-файл содержимого")
    a = ap.parse_args()
    with open(a.content, encoding="utf-8-sig") as f:
        content = json.load(f)
    workdir = os.path.dirname(os.path.abspath(a.content))
    build(a.out, a.num, a.theme, content, workdir)

if __name__ == "__main__":
    main()
