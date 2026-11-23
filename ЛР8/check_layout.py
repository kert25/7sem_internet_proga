# -*- coding: utf-8 -*-
"""Проверка вёрстки страниц лабораторной работы № 8.

Скрипт открывает четыре страницы работы, разбирает их разметку и проверяет
то, что должно быть в макете по заданию: состав блоков, число колонок,
открытие миниатюр в новых вкладках и существование всех локальных файлов,
на которые ссылаются страницы.

Запуск:  py ЛР8/check_layout.py
Код возврата 0 — проверки пройдены, 1 — есть ошибки.
"""

import os
import re
import sys
from html.parser import HTMLParser

BASE = os.path.dirname(os.path.abspath(__file__))

errors = []
checks = []


def ok(message):
    checks.append(message)


def fail(message):
    errors.append(message)


class PageParser(HTMLParser):
    """Собирает то, что нужно для проверок: теги, атрибуты, ссылки, тексты."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.tags = []              # (tag, {attrs})
        self.classes = []           # (tag, set(classes))
        self.hrefs = []             # (tag, href)
        self.srcs = []              # (tag, src)
        self.anchors = []           # (attrs) только <a>
        self.images = []            # attrs <img>
        self.inputs = []            # attrs <input>
        self.textareas = []         # attrs <textarea>
        self.forms = []             # attrs <form>
        self.doctype = False
        self.lang = None
        self.charset = None
        self.title = None
        self._in_title = False
        self._title_parts = []

    def handle_decl(self, decl):
        if decl.strip().lower().startswith("doctype html"):
            self.doctype = True

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.tags.append((tag, attributes))
        classes = set((attributes.get("class") or "").split())
        self.classes.append((tag, classes))

        if tag == "html":
            self.lang = attributes.get("lang")
        if tag == "meta" and (attributes.get("charset") or "").lower() == "utf-8":
            self.charset = "utf-8"
        if tag == "title":
            self._in_title = True
            self._title_parts = []
        if tag == "a" and attributes.get("href"):
            self.hrefs.append((tag, attributes["href"]))
            self.anchors.append(attributes)
        if tag in ("img", "script", "link") and attributes.get("src"):
            self.srcs.append((tag, attributes["src"]))
        if tag == "link" and attributes.get("href"):
            self.hrefs.append((tag, attributes["href"]))
        if tag == "img":
            self.images.append(attributes)
        if tag == "input":
            self.inputs.append(attributes)
        if tag == "textarea":
            self.textareas.append(attributes)
        if tag == "form":
            self.forms.append(attributes)

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = "".join(self._title_parts).strip()

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)

    def has_class(self, tag, name):
        return any(t == tag and name in cs for t, cs in self.classes)

    def count_class(self, name):
        return sum(1 for _, cs in self.classes if name in cs)

    def count_tag(self, tag):
        return sum(1 for t, _ in self.tags if t == tag)

    def named(self, tag, attribute):
        return [a for a in self.inputs if a.get(attribute)]


def load(name):
    path = os.path.join(BASE, name)
    if not os.path.exists(path):
        fail("нет файла страницы: %s" % name)
        return None, None
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    page = PageParser()
    page.feed(source)
    page.close()
    return page, source


def check_common(name, page):
    if not page.doctype:
        fail("%s: нет объявления <!DOCTYPE html>" % name)
    if page.lang != "ru":
        fail("%s: у <html> должен быть lang=\"ru\"" % name)
    if page.charset != "utf-8":
        fail("%s: не указана кодировка <meta charset=\"utf-8\">" % name)
    if not page.title:
        fail("%s: пустой <title>" % name)
    if not page.has_class("header", "topbar") and not page.has_class("header", "portfolio-header"):
        fail("%s: нет шапки страницы (.topbar или .portfolio-header)" % name)
    if page.count_tag("footer") == 0:
        fail("%s: нет подвала" % name)
    if not page.has_class("html", "no-js") and page.count_tag("main") == 0:
        fail("%s: нет элемента <main>" % name)
    # подключены оба стилевых файла: общий и собственный
    css = [href for tag, href in page.hrefs if tag == "link" and href.endswith(".css")]
    if "common.css" not in css:
        fail("%s: не подключён общий файл common.css" % name)
    if len(css) < 2:
        fail("%s: не подключён собственный файл стилей страницы" % name)


def check_assets(name, page):
    for tag, href in page.hrefs:
        if tag != "a":
            continue
        if re.match(r"^(https?:|mailto:|#)", href):
            continue
        target = href.split("#")[0]
        if not target:
            continue
        path = os.path.join(BASE, target)
        if not os.path.exists(path):
            fail("%s: ссылка ведёт на несуществующий файл: %s" % (name, href))
    for _, src in page.srcs:
        if re.match(r"^(https?:|data:)", src):
            continue
        if not os.path.exists(os.path.join(BASE, src)):
            fail("%s: не найден файл ресурса: %s" % (name, src))
    for image in page.images:
        if not image.get("alt"):
            fail("%s: у изображения нет alt: %s" % (name, image.get("src")))


def check_menu_form(page):
    name = "menu-form.html"
    if page.count_class("menu__link") < 5:
        fail("%s: в меню меньше пяти ссылок" % name)
    if page.count_class("comments__item") != 3:
        fail("%s: в ленте должно быть три комментария" % name)
    if page.count_tag("form") != 1:
        fail("%s: на странице должна быть одна форма" % name)
    if not any(a.get("name") == "name" for a in page.inputs):
        fail("%s: в форме нет поля name" % name)
    if not any(a.get("name") == "comment" for a in page.textareas):
        fail("%s: в форме нет поля textarea name=\"comment\"" % name)
    if not any(a.get("type") == "submit" for a in
               [t for tag, t in page.tags if tag == "button"]):
        fail("%s: в форме нет кнопки отправки" % name)
    required = [a for a in page.inputs + page.textareas if "required" in a]
    if len(required) < 3:
        fail("%s: обязательных полей меньше трёх" % name)
    social = [a for a in page.anchors if a.get("class") and "social__link" in a["class"]]
    if len(social) != 3:
        fail("%s: панель соцсетей должна содержать три ссылки" % name)
    for link in social:
        if link.get("target") != "_blank":
            fail("%s: ссылка соцсети должна открываться в новой вкладке" % name)
    with open(os.path.join(BASE, "menu-form.css"), encoding="utf-8") as handle:
        css = handle.read()
    for item in ("float: left", "clear: both", "position: fixed", ":has(:checked)"):
        if item not in css:
            fail("menu-form.css: нет приёма вёрстки «%s»" % item)
    ok("%s: меню, лента комментариев, форма и фиксированная панель соцсетей" % name)


def check_news(page):
    name = "news.html"
    columns = page.count_class("news-column")
    if columns != 3:
        fail("%s: колонок %d, а по заданию их три" % (name, columns))
    if len(page.images) < 3:
        fail("%s: изображений меньше трёх" % name)
    if page.count_class("news-card") < 6:
        fail("%s: карточек новостей меньше шести" % name)
    with open(os.path.join(BASE, "news.css"), encoding="utf-8") as handle:
        css = handle.read()
    if "display: grid" not in css or "grid-template-columns" not in css:
        fail("news.css: сетка должна быть собрана через CSS Grid")
    ok("%s: %d колонки, %d изображения, %d карточки" %
       (name, columns, len(page.images), page.count_class("news-card")))


def check_gallery(page):
    name = "gallery.html"
    items = page.count_class("gallery-item")
    if items != 6:
        fail("%s: миниатюр %d, а по эскизу их шесть" % (name, items))
    thumbs = [a for a in page.anchors if a.get("class") and "gallery-item__link" in a["class"]]
    if len(thumbs) != 6:
        fail("%s: ссылок-миниатюр %d, ожидается 6" % (name, len(thumbs)))
    for link in thumbs:
        if link.get("target") != "_blank":
            fail("%s: миниатюра %s не открывается в новой вкладке" % (name, link.get("href")))
        href = link.get("href") or ""
        if not os.path.exists(os.path.join(BASE, href)):
            fail("%s: нет полноразмерного файла %s" % (name, href))
    if page.count_class("categories") == 0:
        fail("%s: нет полосы категорий внизу страницы" % name)
    ok("%s: %d миниатюр, все открываются в новой вкладке" % (name, items))


def check_portfolio(page):
    name = "portfolio.html"
    if page.count_class("work") < 8:
        fail("%s: карточек работ меньше восьми" % name)
    if page.count_class("hero") == 0:
        fail("%s: нет первого экрана (.hero)" % name)
    if page.count_class("technique") != 3:
        fail("%s: в блоке техник макетирования должно быть три карточки" % name)
    with open(os.path.join(BASE, "portfolio.css"), encoding="utf-8") as handle:
        css = handle.read()
    for item in ("display: flex", "flex-wrap: wrap", "position: sticky"):
        if item not in css:
            fail("portfolio.css: нет приёма вёрстки «%s»" % item)
    ok("%s: собственный макет на Flexbox, %d карточек работ" %
       (name, page.count_class("work")))


def main():
    pages = {}
    for name in ("menu-form.html", "news.html", "gallery.html", "portfolio.html"):
        page, _ = load(name)
        if page is None:
            continue
        pages[name] = page
        check_common(name, page)
        check_assets(name, page)

    if "menu-form.html" in pages:
        check_menu_form(pages["menu-form.html"])
    if "news.html" in pages:
        check_news(pages["news.html"])
    if "gallery.html" in pages:
        check_gallery(pages["gallery.html"])
    if "portfolio.html" in pages:
        check_portfolio(pages["portfolio.html"])

    for item in checks:
        print("OK   " + item)
    for item in errors:
        print("FAIL " + item)

    print("\nИтого: проверок пройдено %d, ошибок %d" % (len(checks), len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
