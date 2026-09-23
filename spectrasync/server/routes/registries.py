"""Registries discovery endpoint."""

from __future__ import annotations

from fastapi import APIRouter
import spectrasync as ss
from ..schemas import RegistriesResponse, RegistryItem

router = APIRouter(tags=["registries"])


@router.get("/registries", response_model=RegistriesResponse)
def get_registries() -> RegistriesResponse:
    """Return available plugin options registered in spectrasync."""
    regs = ss.registries()
    
    def _items(kind: str) -> list[RegistryItem]:
        reg = regs.get(kind)
        if not reg:
            return []
        return [RegistryItem(name=name) for name in reg.names()]

    return RegistriesResponse(
        window=_items("window"),
        subpixel=_items("subpixel"),
        reducer=_items("reducer"),
        detector=_items("detector"),
        overlay=_items("overlay"),
        filter=_items("filter"),
    )
