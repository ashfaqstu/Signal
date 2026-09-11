"""A tiny name -> callable registry.

This is the extension mechanism for the whole project. Every family of
interchangeable algorithms (window functions, sub-pixel refiners, temporal
reducers, change detectors, UI pages) is a `Registry`. Adding a new option is
one decorated function -- no edits anywhere else, nothing to wire up.

    from spectrasync.registry import Registry

    WINDOWS = Registry("window")

    @WINDOWS.register("hann", doc="Raised cosine, zero at the edges")
    def _hann(n):
        return np.hanning(n)

    WINDOWS["hann"](64)      # call it
    WINDOWS.names()          # -> ["hann", ...]  (drives every UI dropdown)
"""

from __future__ import annotations


class Registry:
    """An ordered, self-documenting dict of named callables."""

    def __init__(self, kind):
        self.kind = kind
        self._items = {}
        self._docs = {}

    def register(self, name, doc=""):
        """Decorator. Registers the function under `name` and returns it
        unchanged, so the function is still directly importable and callable."""
        def deco(fn):
            if name in self._items:
                raise KeyError(f"{self.kind} {name!r} is already registered")
            self._items[name] = fn
            self._docs[name] = doc or (fn.__doc__ or "").strip().split("\n")[0]
            return fn
        return deco

    def add(self, name, fn, doc=""):
        """Non-decorator form, for registering something defined elsewhere."""
        return self.register(name, doc)(fn)

    def __getitem__(self, name):
        try:
            return self._items[name]
        except KeyError:
            raise KeyError(
                f"unknown {self.kind} {name!r}; available: {self.names()}"
            ) from None

    def __contains__(self, name):
        return name in self._items

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def names(self):
        """Registration order -- drives dropdown order in the UI."""
        return list(self._items)

    def doc(self, name):
        return self._docs.get(name, "")

    def items(self):
        return self._items.items()

    def describe(self):
        """[(name, one-line doc), ...] -- for help text and UI captions."""
        return [(n, self._docs[n]) for n in self._items]
