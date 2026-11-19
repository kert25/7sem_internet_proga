"""Смысловая проверка ЛР7: стилевой файл и его подключение к страницам.

Запуск: py ЛР7/check_css.py  (из корня проекта)
Код возврата 0 — все проверки пройдены, 1 — есть замечания.
Сообщения печатаются латиницей, чтобы вывод не зависел от кодовой страницы
консоли Windows.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "ЛР7" / "styles.css"
LABS = ["ЛР1", "ЛР2", "ЛР3", "ЛР4", "ЛР5", "ЛР6"]
LAB_LINK = '<link rel="stylesheet" href="../ЛР7/styles.css">'
OWN_LINK = '<link rel="stylesheet" href="styles.css">'

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    check(CSS.is_file(), "styles.css not found in ЛР7/")
    if not failures:
        css = CSS.read_text(encoding="utf-8-sig")
        check(len(css.splitlines()) >= 100, "styles.css is unexpectedly short")
        check(css.count("{") == css.count("}"), "braces in styles.css are unbalanced")

        patterns = {
            "element selector": r"(?m)^\s*(?:blockquote|body|table|th|td|a)\b[^{]*\{",
            "class selector": r"\.demo-chip\s*\{",
            "id selector": r"#demo-target\s*\{",
            "descendant selector": r"\.demo-tree p\s*\{",
            "child selector": r"\.demo-child\s*>\s*p\s*\{",
            "adjacent sibling selector": r"h4\s*\+\s*p\s*\{",
            "general sibling selector": r"h4\s*~\s*p\s*\{",
            "attribute selector": r'\[href\^="https"\]',
            "pseudo-class": r":nth-child\(odd\)",
            "pseudo-element": r"::first-letter",
            "css variable": r"--brand:",
            "var() usage": r"var\(--brand\)",
            "media query": r"@media",
        }
        for label, pattern in patterns.items():
            check(re.search(pattern, css) is not None, "styles.css has no %s" % label)

        pages = []
        for lab in LABS:
            pages.extend(sorted((ROOT / lab).glob("*.html")))
        check(len(pages) == 25, "expected 25 earlier pages, found %d" % len(pages))
        for page in pages:
            text = page.read_text(encoding="utf-8-sig")
            relative = page.relative_to(ROOT).as_posix()
            check(
                LAB_LINK in text,
                "%s does not link ../ЛР7/styles.css" % relative,
            )
            link_at = text.find("ЛР7/styles.css")
            style_at = text.lower().find("<style")
            if link_at != -1 and style_at != -1:
                check(
                    link_at < style_at,
                    "%s links the stylesheet after its own <style>" % relative,
                )

        for name in ("index.html", "selectors.html"):
            page = ROOT / "ЛР7" / name
            check(page.is_file(), "ЛР7/%s is missing" % name)
            if page.is_file():
                text = page.read_text(encoding="utf-8-sig")
                check(OWN_LINK in text, "ЛР7/%s does not link styles.css" % name)

    if failures:
        print("CHECK FAILED: %d problem(s)" % len(failures))
        for item in failures:
            print("  - " + item)
        return 1

    print("CHECK OK: styles.css is linked by 25 earlier pages and 2 pages of ЛР7")
    print("CHECK OK: element, class, id and combined selectors are present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
