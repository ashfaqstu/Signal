"""Layer and Run memory stores with LRU eviction and lazy image encoding."""

from __future__ import annotations

import collections
import uuid
from dataclasses import dataclass
from typing import Any

import numpy as np

from . import config, encode


@dataclass
class Layer:
    id: str
    name: str
    group: str
    kind: str  # "image", "mask", "heatmap"
    array: np.ndarray
    width: int
    height: int
    cmap: str = "inferno"
    encoded_bytes: bytes | None = None


class LayerStore:
    def __init__(self):
        self._layers: dict[str, Layer] = {}

    def put(self, arr: np.ndarray | list, kind: str, name: str,
            group: str = "Outputs", cmap: str = "inferno") -> Layer:
        a = np.asarray(arr)
        h, w = a.shape[:2]
        layer_id = uuid.uuid4().hex[:16]
        layer = Layer(
            id=layer_id,
            name=name,
            group=group,
            kind=kind,
            array=a,
            width=w,
            height=h,
            cmap=cmap,
            encoded_bytes=None,
        )
        self._layers[layer_id] = layer
        return layer

    def get_layer(self, layer_id: str) -> Layer | None:
        return self._layers.get(layer_id)

    def get_bytes(self, layer_id: str) -> bytes | None:
        layer = self._layers.get(layer_id)
        if not layer:
            return None
        if layer.encoded_bytes is None:
            if layer.kind == "heatmap":
                layer.encoded_bytes = encode.heatmap_png(layer.array, cmap=layer.cmap)
            else:
                layer.encoded_bytes = encode.to_png(layer.array)
        return layer.encoded_bytes

    def delete(self, layer_id: str) -> None:
        self._layers.pop(layer_id, None)


@dataclass
class RunEntry:
    run_id: str
    payload: Any
    layer_ids: list[str]


class RunStore:
    def __init__(self, layer_store: LayerStore, max_runs: int = config.MAX_RUNS_KEPT):
        self._runs: collections.OrderedDict[str, RunEntry] = collections.OrderedDict()
        self._layer_store = layer_store
        self._max_runs = max_runs

    def put(self, run_id: str, payload: Any, layer_ids: list[str]) -> None:
        if run_id in self._runs:
            self._runs.move_to_end(run_id)
            self._runs[run_id] = RunEntry(run_id, payload, layer_ids)
            return

        while len(self._runs) >= self._max_runs:
            _, evicted = self._runs.popitem(last=False)
            for lid in evicted.layer_ids:
                self._layer_store.delete(lid)

        self._runs[run_id] = RunEntry(run_id, payload, layer_ids)

    def get(self, run_id: str) -> Any | None:
        entry = self._runs.get(run_id)
        if entry:
            self._runs.move_to_end(run_id)
            return entry.payload
        return None

    def get_entry(self, run_id: str) -> RunEntry | None:
        entry = self._runs.get(run_id)
        if entry:
            self._runs.move_to_end(run_id)
            return entry
        return None


layer_store = LayerStore()
run_store = RunStore(layer_store)
