"""Media assets endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, UploadFile, Query
from PIL import Image

from ..media import media_store, Media
from ..schemas import MediaItem, VideoFrameItem
from ..encode import thumb_jpeg
from ..layers import layer_store
import spectrasync as ss

router = APIRouter(prefix="/media", tags=["media"])


def _to_media_item(m: Media) -> MediaItem:
    return MediaItem(
        id=m.id,
        name=m.name,
        kind=m.kind,
        path=str(m.path),
        group=m.group,
        sample=m.sample,
        width=m.width,
        height=m.height,
        n_frames=m.n_frames,
    )


@router.get("", response_model=list[MediaItem])
def list_media() -> list[MediaItem]:
    """List all registered sample and uploaded media items."""
    return [_to_media_item(m) for m in media_store.list_all()]


@router.post("", response_model=list[MediaItem])
async def upload_media(files: list[UploadFile]) -> list[MediaItem]:
    """Upload one or more media files."""
    results = []
    for f in files:
        m = await media_store.import_upload(f)
        results.append(_to_media_item(m))
    return results


@router.delete("/{media_id}")
def delete_media(media_id: str) -> dict[str, bool]:
    """Delete an uploaded media file (sample files cannot be deleted)."""
    ok = media_store.delete(media_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot delete this media item")
    return {"ok": True}


@router.get("/{media_id}/thumb.jpg")
def get_media_thumbnail(
    media_id: str,
    size: int = Query(160, ge=32, le=960, description="Longest side in px"),
) -> Response:
    """Retrieve a fast JPEG thumbnail for media asset."""
    media = media_store.get(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    if not media.path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    try:
        if media.kind == "image":
            arr = ss.load_rgb(media.path, max_side=size)
        else:
            frames = ss.read_video(media.path, max_frames=1, max_side=size, gray=False)
            if not frames:
                raise ValueError("No frames could be read from video")
            arr = frames[0]

        jpeg_bytes = thumb_jpeg(arr, max_side=size)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "max-age=3600"},
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to generate thumbnail: {e}")


@router.get("/{media_id}/frames", response_model=list[VideoFrameItem])
def get_video_frames(
    media_id: str,
    max_frames: int = Query(24, alias="maxFrames"),
    step: int = Query(1, alias="step"),
) -> list[VideoFrameItem]:
    """Extract sample frame thumbnails from a video before a full run."""
    media = media_store.get(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    if media.kind != "video":
        raise HTTPException(status_code=400, detail="Media is not a video")

    try:
        frames = media_store.load_video(
            media_id,
            max_frames=max_frames,
            step=step,
            max_side=160,
            gray=False,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail={"code": "no_video_backend", "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=422, detail={"code": "bad_media", "message": str(e)})

    items = []
    for i, f in enumerate(frames):
        layer = layer_store.put(f, kind="image", name=f"frame_{i}", group="VideoFrames")
        items.append(VideoFrameItem(index=i, thumb_url=f"/api/layers/{layer.id}.png"))

    return items
