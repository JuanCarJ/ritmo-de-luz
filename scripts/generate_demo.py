from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "core"))

samplesDir = root / "samples"
demoDir = root / "artifacts" / "demo"
demoAudioDir = demoDir / "audio"
demoImageDir = demoDir / "images"
publicAudios = [
    ("menu-loop", "menu-loop.wav", "Loop musical CC0 para ritmo y ataques."),
    ("peaceful-forest", "peaceful-forest.wav", "Textura ambiental CC0 para suavizado."),
    ("space-ranger", "space-ranger.wav", "Loop downtempo CC0 para cambios espectrales."),
]


def ensureImage() -> Path:
    samplesDir.mkdir(exist_ok=True)
    imagePath = samplesDir / "demo-image.png"
    if not imagePath.exists():
        width, height = 960, 540
        y, x = np.mgrid[0:height, 0:width]
        red = np.clip(32 + 190 * x / width + 22 * np.sin(y / 35), 0, 255)
        green = np.clip(18 + 70 * y / height + 55 * np.sin(x / 48), 0, 255)
        blue = np.clip(90 + 130 * (1 - x / width) + 24 * np.cos((x + y) / 50), 0, 255)
        image = Image.fromarray(np.uint8(np.dstack([red, green, blue])), "RGB")
        draw = ImageDraw.Draw(image)
        draw.ellipse((280, 110, 680, 510), outline=(255, 220, 160), width=8)
        draw.text((42, 42), "RITMO DE LUZ", fill=(255, 240, 220))
        image.save(imagePath)
    return imagePath


def ensureImages() -> list[dict[str, str]]:
    demoImageDir.mkdir(parents=True, exist_ok=True)
    width, height = 960, 540
    y, x = np.mgrid[0:height, 0:width]
    sources = [
        ("aurora", "Aurora", np.dstack([40 + 180 * x / width, 35 + 130 * y / height, 150 + 80 * np.sin(x / 80)])),
        ("pulso", "Pulso", np.dstack([180 + 60 * np.sin(x / 45), 35 + 170 * x / width, 45 + 150 * y / height])),
        ("cosmos", "Cosmos", np.dstack([25 + 80 * y / height, 30 + 70 * x / width, 120 + 100 * np.cos((x + y) / 55)])),
    ]
    images = []
    for imageId, name, values in sources:
        imagePath = demoImageDir / f"{imageId}.png"
        if not imagePath.exists():
            Image.fromarray(np.uint8(np.clip(values, 0, 255)), "RGB").save(imagePath)
        images.append({"id": imageId, "name": name, "imageUrl": f"/artifacts/demo/images/{imagePath.name}"})
    return images


def trimAudio(sourcePath: Path, targetPath: Path, seconds: int = 20) -> None:
    samples, sampleRate = sf.read(sourcePath, dtype="float32", always_2d=False)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    targetSamples = int(sampleRate * seconds)
    samples = samples[:targetSamples]
    if len(samples) < targetSamples:
        samples = np.pad(samples, (0, targetSamples - len(samples)))
    sf.write(targetPath, samples, sampleRate)


def main() -> int:
    from ritmo_de_luz_core.pipeline import generateMosaicMp4

    imagePath = ensureImage()
    images = ensureImages()
    demoDir.mkdir(parents=True, exist_ok=True)
    demoAudioDir.mkdir(parents=True, exist_ok=True)
    demos = []
    for audioId, audioName, description in publicAudios:
        sourcePath = samplesDir / audioName
        if not sourcePath.exists():
            raise FileNotFoundError(f"Falta el audio público: {sourcePath}")
        trimmedPath = demoAudioDir / f"{audioId}.wav"
        trimAudio(sourcePath, trimmedPath, seconds=20)
        outputPath = demoDir / f"ritmo-de-luz-{audioId}.mp4"
        generateMosaicMp4(image=imagePath, audio=trimmedPath, output=str(outputPath), useMl=True)
        demos.append({
            "id": audioId,
            "name": audioId.replace("-", " ").title(),
            "audio": audioName,
            "audioUrl": f"/artifacts/demo/audio/{trimmedPath.name}",
            "videoUrl": f"/artifacts/demo/{outputPath.name}",
            "description": description,
            "durationSeconds": 20,
            "mlEnabled": True,
        })

    Image.open(imagePath).resize((960, 540)).save(demoDir / "ritmo-de-luz-demo-poster.jpg", quality=90)
    manifest = {
        "name": "Ritmo de Luz",
        "bands": 12,
        "mlEnabled": True,
        "fps": 30,
        "durationSeconds": 20,
        "videoUrl": demos[0]["videoUrl"],
        "demos": demos,
        "images": images,
    }
    (demoDir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
