"""Pydantic request and response schemas for SpectraSync Studio API."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model with camelCase serialization and deserialization."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class HealthResponse(CamelModel):
    ok: bool = True
    version: str
    video: bool


class RegistryItem(CamelModel):
    name: str


class RegistriesResponse(CamelModel):
    window: list[RegistryItem] = []
    subpixel: list[RegistryItem] = []
    reducer: list[RegistryItem] = []
    detector: list[RegistryItem] = []
    overlay: list[RegistryItem] = []
    filter: list[RegistryItem] = []


class MediaItem(CamelModel):
    id: str
    name: str
    kind: Literal["image", "video"]
    path: str
    group: str
    sample: bool
    width: int
    height: int
    n_frames: int | None = None


class VideoFrameItem(CamelModel):
    index: int
    thumb_url: str


class Readout(CamelModel):
    key: str
    label: str
    value: float | int | str
    unit: str = ""
    fmt: str = ""  # "+.3f", ".2f", "d", "pct", etc.
    tone: Literal["default", "ok", "warn", "bad", "muted"] = "default"


class LayerRef(CamelModel):
    id: str
    name: str
    group: str
    kind: str  # "image", "mask", "heatmap"
    width: int
    height: int
    url: str


class Marker(CamelModel):
    layer: str
    type: Literal["crosshair", "box"]
    x: float
    y: float
    w: float = 0.0
    h: float = 0.0


class FrameRef(CamelModel):
    index: int
    name: str
    layers: dict[str, str]  # name -> layer url
    meta: dict[str, Any] = {}


class ChartSeries(CamelModel):
    name: str
    values: list[float]
    role: Literal["primary", "reference"] = "primary"


class Chart(CamelModel):
    id: str
    kind: Literal["line", "bar"]
    x: list[float] | list[str]
    series: list[ChartSeries]


class Table(CamelModel):
    columns: list[str]
    rows: list[list[Any]]


class RunResult(CamelModel):
    run_id: str
    workspace: str
    elapsed_ms: int
    verdict: Literal["locked", "marginal", "no lock"] | None = None
    readouts: list[Readout] = []
    layers: list[LayerRef] = []
    markers: list[Marker] = []
    frames: list[FrameRef] = []
    charts: list[Chart] = []
    table: Table | None = None
    flags: list[str] = []


class PixelTimeseriesResponse(CamelModel):
    signal: list[float]
    median: float
    freq: list[float]
    spectrum: list[float]


# --- Workspace Parameter Schemas ---

class AlignParams(CamelModel):
    source: Literal["pair", "synthetic", "video"] = "synthetic"
    a_id: str | None = None
    b_id: str | None = None
    media_id: str | None = None
    a_index: int = 0
    b_index: int = 1
    base_id: str | None = None
    dy: float = 12.5
    dx: float = -7.5
    noise: float = 0.0
    window: str = "hann"
    subpixel: str = "parabolic"
    beta: float = 1.0
    lowpass: float = 0.0
    overlay: str = "anaglyph"
    tile: int = 32
    alpha: float = 0.5


class RotateParams(CamelModel):
    source: Literal["pair", "synthetic", "video"] = "pair"
    a_id: str | None = None
    b_id: str | None = None
    media_id: str | None = None
    a_index: int = 0
    b_index: int = 1
    max_side: int = 704
    base_id: str | None = None
    angle: float = 20.0
    scale: float = 1.20
    dy: float = 9.0
    dx: float = -14.0
    noise: float = 0.0
    robust: bool = True
    n_theta: int = 720
    n_rho: int = 512
    overlay: str = "anaglyph"


class StackParams(CamelModel):
    source: Literal["photos", "video", "synthetic"] = "photos"
    media_ids: list[str] = []
    max_side: int = 800
    colour: bool = True
    clean_id: str | None = None
    media_id: str | None = None
    frames: int = 16
    step: int = 1
    base_id: str | None = None
    n: int = 16
    noise: float = 0.12
    shift: float = 5.0
    reducer: str = "mean"
    align: bool = True
    compare: bool = True


class RemoveParams(CamelModel):
    source: Literal["photos", "synthetic", "video"] = "photos"
    media_ids: list[str] = []
    max_side: int = 640
    colour: bool = True
    mode: Literal["translation", "auto", "similarity"] = "auto"
    base_id: str | None = None
    n: int = 12
    radius: int = 26
    noise: float = 0.01
    shake: float = 4.0
    media_id: str | None = None
    frames: int = 24
    step: int = 2
    reducer: str = "shorth"
    compare_filters: bool = True


class HighlightParams(CamelModel):
    source: Literal["photos", "synthetic", "video"] = "photos"
    media_ids: list[str] = []
    max_side: int = 640
    colour: bool = True
    mode: Literal["translation", "auto", "similarity"] = "auto"
    reducer: str = "shorth"
    base_id: str | None = None
    n: int = 12
    radius: int = 26
    noise: float = 0.01
    media_id: str | None = None
    frames: int = 24
    step: int = 2
    detector: str = "bandpass"
    low: float = 0.02
    high: float = 0.20
    k: float = 3.0
    smooth: float = 1.5
    min_area: int = 40


class SpectrumParams(CamelModel):
    base_id: str | None = None
    dy: float = 12.0
    dx: float = -8.0
