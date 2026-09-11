"""Page registry -- the UI extension point.

Adding a screen is ONE file in app/pages/ containing one decorated function:

    from app.registry import page

    @page("My Feature", order=50, icon="*")
    def render():
        ...

Nothing else changes: no imports to edit, no router to touch, no list to append.
`app/pages/__init__.py` imports every module in the folder, so the decorator
runs and the page appears in the sidebar in `order`.
"""

from __future__ import annotations

_PAGES = []


def page(title, order=100, icon="", help=""):
    def deco(fn):
        _PAGES.append({"title": title, "order": order, "icon": icon,
                       "help": help or (fn.__doc__ or "").strip().split("\n")[0],
                       "render": fn})
        return fn
    return deco


def pages():
    return sorted(_PAGES, key=lambda p: (p["order"], p["title"]))


def labels():
    return [f"{p['icon']} {p['title']}".strip() for p in pages()]


def by_label(label):
    for p in pages():
        if f"{p['icon']} {p['title']}".strip() == label:
            return p
    return pages()[0]
