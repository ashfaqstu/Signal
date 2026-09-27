"""Tests for the SpectraSync Studio FastAPI backend."""

from __future__ import annotations

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

import spectrasync as ss
from server.main import create_app
from server import config


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health_check(client: TestClient):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["version"] == ss.__version__
    assert isinstance(data["video"], bool)


def test_registries(client: TestClient):
    res = client.get("/api/registries")
    assert res.status_code == 200
    data = res.json()
    assert [x["name"] for x in data["window"]] == ss.WINDOWS.names()
    assert [x["name"] for x in data["subpixel"]] == ss.SUBPIXEL.names()
    assert [x["name"] for x in data["reducer"]] == ss.REDUCERS.names()
    assert [x["name"] for x in data["detector"]] == ss.DETECTORS.names()
    assert [x["name"] for x in data["overlay"]] == ss.OVERLAYS.names()


def test_media_list(client: TestClient):
    res = client.get("/api/media")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    # Check sample items exist
    assert any(m["sample"] for m in data)


# --- Workspace Tests with Synthetic Sources ---

def test_run_align_synthetic(client: TestClient):
    payload = {
        "source": "synthetic",
        "dy": 12.5,
        "dx": -7.5,
        "noise": 0.0,
        "window": "hann",
        "subpixel": "parabolic",
        "beta": 1.0,
        "lowpass": 0.0,
        "overlay": "anaglyph",
    }
    res = client.post("/api/run/align", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["workspace"] == "align"
    assert data["verdict"] == "locked"

    # Layer names
    layer_names = [l["name"] for l in data["layers"]]
    assert "A" in layer_names
    assert "B" in layer_names
    assert "B restored" in layer_names
    assert "Overlay" in layer_names
    assert "|F₁|" in layer_names
    assert "r(x,y)" in layer_names

    # Check that layer URLs return image/png
    for layer in data["layers"][:3]:
        l_res = client.get(layer["url"])
        assert l_res.status_code == 200
        assert l_res.headers["content-type"] == "image/png"

    # Numeric sanity checks
    readouts = {r["key"]: r["value"] for r in data["readouts"]}
    assert abs(float(readouts["dy"]) - 12.5) < 0.1
    assert abs(float(readouts["dx"]) - (-7.5)) < 0.1
    assert float(readouts["psnr_after"]) > float(readouts["psnr_before"])


def test_run_rotate_synthetic(client: TestClient):
    payload = {
        "source": "synthetic",
        "angle": 20.0,
        "scale": 1.20,
        "dy": 9.0,
        "dx": -14.0,
        "noise": 0.0,
        "robust": True,
        "nTheta": 720,
        "nRho": 512,
        "overlay": "anaglyph",
    }
    res = client.post("/api/run/rotate", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["workspace"] == "rotate"

    layer_names = [l["name"] for l in data["layers"]]
    assert "A" in layer_names
    assert "B" in layer_names
    assert "B restored" in layer_names
    assert "log-polar A" in layer_names
    assert "ρθ correlation" in layer_names

    readouts = {r["key"]: r["value"] for r in data["readouts"]}
    assert abs(float(readouts["rotation"]) - 20.0) < 1.0
    assert abs(float(readouts["scale"]) - 1.20) < 0.05


def test_run_stack_synthetic(client: TestClient):
    payload = {
        "source": "synthetic",
        "n": 8,
        "noise": 0.10,
        "shift": 4.0,
        "reducer": "mean",
        "align": True,
        "compare": True,
    }
    res = client.post("/api/run/stack", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["workspace"] == "stack"

    layer_names = [l["name"] for l in data["layers"]]
    assert "Raw" in layer_names
    assert "Stacked" in layer_names
    assert "median" in layer_names

    assert len(data["frames"]) == 8
    assert len(data["charts"]) > 0
    assert data["table"] is not None

    readouts = {r["key"]: r["value"] for r in data["readouts"]}
    assert float(readouts["gain"]) > 0


def test_run_remove_synthetic_and_pixel(client: TestClient):
    payload = {
        "source": "synthetic",
        "n": 8,
        "radius": 20,
        "noise": 0.01,
        "shake": 3.0,
        "reducer": "shorth",
        "compareFilters": True,
    }
    res = client.post("/api/run/remove", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["workspace"] == "remove"

    layer_names = [l["name"] for l in data["layers"]]
    assert "Frame 0" in layer_names
    assert "Plate" in layer_names
    assert any("mean" in l for l in layer_names)  # from compareFilters

    assert len(data["markers"]) == 1
    assert data["markers"][0]["layer"] == "Plate"
    mx = int(data["markers"][0]["x"])
    my = int(data["markers"][0]["y"])

    # Test /pixel endpoint
    run_id = data["runId"]
    pix_res = client.get(f"/api/runs/{run_id}/pixel?x={mx}&y={my}")
    assert pix_res.status_code == 200, pix_res.text
    pix_data = pix_res.json()
    assert len(pix_data["signal"]) == 8
    assert len(pix_data["freq"]) == len(pix_data["spectrum"])


def test_run_highlight_synthetic(client: TestClient):
    payload = {
        "source": "synthetic",
        "n": 8,
        "radius": 20,
        "noise": 0.01,
        "detector": "bandpass",
        "low": 0.02,
        "high": 0.20,
        "k": 2.5,
        "smooth": 1.5,
        "minArea": 30,
    }
    res = client.post("/api/run/highlight", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["workspace"] == "highlight"
    assert "Plate" in [l["name"] for l in data["layers"]]
    assert len(data["frames"]) == 8
    assert "photo" in data["frames"][0]["layers"]
    assert "overlay" in data["frames"][0]["layers"]


def test_run_spectrum_synthetic(client: TestClient):
    payload = {
        "dy": 12.0,
        "dx": -8.0,
    }
    res = client.post("/api/run/spectrum", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["workspace"] == "spectrum"
    layer_names = [l["name"] for l in data["layers"]]
    assert "f₁ | f₂" in layer_names
    assert "|F₁|" in layer_names
    assert "phase swap" in layer_names
    assert "∠R" in layer_names
    assert "r(x,y)" in layer_names
    assert "log-polar A" in layer_names


# --- Sample Fallback Tests ---

@pytest.mark.skipif(not (config.ROOT / "new_image/3").exists(), reason="Sample pair missing")
def test_run_rotate_sample(client: TestClient):
    res = client.post("/api/run/rotate", json={"source": "pair", "maxSide": 512})
    assert res.status_code == 200


@pytest.mark.skipif(not (config.ROOT / "new_image/2_noisy/set_1").exists(), reason="Sample noisy set missing")
def test_run_stack_sample(client: TestClient):
    res = client.post("/api/run/stack", json={"source": "photos", "maxSide": 512, "compare": False})
    assert res.status_code == 200


@pytest.mark.skipif(not (config.ROOT / "new_image/1").exists(), reason="Sample crowd set missing")
def test_run_remove_sample(client: TestClient):
    res = client.post("/api/run/remove", json={"source": "photos", "maxSide": 512, "compareFilters": False})
    assert res.status_code == 200


# --- Exports and Error Handlers ---

def test_export_endpoints(client: TestClient):
    # Run align first
    res = client.post("/api/run/align", json={"source": "synthetic", "dy": 5.0, "dx": -5.0})
    assert res.status_code == 200
    run_id = res.json()["runId"]

    # Export layer
    exp_res = client.get(f"/api/runs/{run_id}/export?layer=Overlay&format=png")
    assert exp_res.status_code == 200
    assert exp_res.headers["content-type"] == "image/png"
    assert "attachment" in exp_res.headers["content-disposition"]


def test_bad_request_codes(client: TestClient):
    # Pair with missing items
    res = client.post("/api/run/align", json={"source": "pair", "aId": "invalid_1", "bId": "invalid_2"})
    assert res.status_code == 422
    assert "need_two_images" in str(res.json())
