import io

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from apps.api.app.main import app


def test_health_and_demo_contract():
    with TestClient(app) as client:
        health = client.get("/health")
        demo = client.get("/api/demo")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert demo.status_code == 200
    payload = demo.json()
    demos = payload["demos"]
    assert payload["bands"] == 12 and len(demos) == 5
    # Ninguna imagen ni audio se repite entre ejemplos.
    assert len({d["imageUrl"] for d in demos}) == len({d["audioUrl"] for d in demos}) == len(demos)


def test_render_rejects_too_short_audio():
    audio = io.BytesIO()
    sf.write(audio, np.zeros(22050 * 3, dtype=np.float32), 22050, format="WAV")
    image = io.BytesIO()
    from PIL import Image

    Image.new("RGB", (32, 32), (200, 100, 50)).save(image, format="PNG")
    with TestClient(app) as client:
        response = client.post("/api/render", files={
            "image": ("a.png", image.getvalue(), "image/png"),
            "audio": ("a.wav", audio.getvalue(), "audio/wav"),
        })
    assert response.status_code == 422
    assert "10 s" in response.json()["detail"]
