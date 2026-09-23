"""Layer PNG retrieval endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from ..layers import layer_store

router = APIRouter(tags=["layers"])


@router.get("/layers/{layer_id}.png")
def get_layer_png(layer_id: str) -> Response:
    """Retrieve rendered PNG bytes for a given layer ID."""
    png_bytes = layer_store.get_bytes(layer_id)
    if png_bytes is None:
        raise HTTPException(status_code=404, detail="Layer not found")
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "max-age=3600, immutable"},
    )
