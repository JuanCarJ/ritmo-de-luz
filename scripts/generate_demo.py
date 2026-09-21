"""Genera las tres demos precargadas: clip de entrada, MP4, póster y análisis."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "core"))

samplesDir = root / "samples"
demoDir = root / "artifacts" / "demo"
INPUT_SECONDS = 30  # el enunciado pide un audio de entrada de 20–40 s

# Cada demo es una pareja fija imagen + audio: lo que se ve es exactamente lo que se renderizó.
DEMOS = [
    {"id": "menu-loop", "title": "Menu Loop", "audio": "menu-loop.wav", "image": "dalia.jpg",
     "mood": "Loop rítmico con golpes marcados."},
    {"id": "cyberpunk", "title": "Cyberpunk Moonlight Sonata", "audio": "cyberpunk-moonlight-sonata.mp3",
     "image": "aurora.jpg", "mood": "Electrónica: bombo constante."},
    {"id": "battle-theme", "title": "Battle Theme A", "audio": "battle-theme-a.mp3", "image": "carina.jpg",
     "mood": "Orquesta: cuerdas y metales."},
    {"id": "space-ranger", "title": "Space Ranger", "audio": "space-ranger.wav", "image": "pagoda.jpg",
     "mood": "Downtempo con bajo profundo."},
    {"id": "peaceful-forest", "title": "Peaceful Forest", "audio": "peaceful-forest.wav", "image": "coral.png",
     "mood": "Ambiental: casi sin golpes."},
]


CREDITS = ("Imágenes: vultilion y danielbuechele (Flickr, CC BY 2.0); Stephan Sprinz (Wikimedia Commons, "
           "CC BY 4.0); NASA/ESA/Hubble y NOAA Fisheries (dominio público). Música: Akikazer, Samza, Nostromo, "
           "Joth y cynicmusic (OpenGameArt, CC0).")


def prepareImages() -> None:
    """Copia las fotos CC BY 2.0 que distribuye scikit-learn (ver docs/academic/media-attributions.md)."""
    from sklearn.datasets import images as sklearnImages

    source = Path(sklearnImages.__file__).parent
    for name, target in (("flower.jpg", "dalia.jpg"), ("china.jpg", "pagoda.jpg")):
        if not (samplesDir / target).exists():
            shutil.copy(source / name, samplesDir / target)


def inputClip(sourcePath: Path, targetPath: Path, seconds: int = INPUT_SECONDS) -> None:
    """Deja un clip de entrada de `seconds`; si el original es más corto (loop), lo repite."""
    samples, sampleRate = sf.read(sourcePath, dtype="float32", always_2d=True)
    samples = samples.mean(axis=1)
    target = int(sampleRate * seconds)
    if samples.size < target:
        samples = np.tile(samples, int(np.ceil(target / samples.size)))
    sf.write(targetPath, samples[:target], sampleRate)


def main() -> int:
    from ritmo_de_luz_core.pipeline import renderVideo

    prepareImages()
    for folder in ("audio", "images", "analysis"):
        (demoDir / folder).mkdir(parents=True, exist_ok=True)
    demos = []
    for demo in DEMOS:
        demoId = demo["id"]
        clip = demoDir / "audio" / f"{demoId}.wav"
        inputClip(samplesDir / demo["audio"], clip)
        image = demoDir / "images" / demo["image"]
        shutil.copy(samplesDir / demo["image"], image)
        video = demoDir / f"{demoId}.mp4"
        poster = demoDir / f"{demoId}.jpg"
        print(f"Renderizando {demo['title']}...", flush=True)
        analysis = renderVideo(image, clip, video, posterPath=poster)
        (demoDir / "analysis" / f"{demoId}.json").write_text(json.dumps(analysis), encoding="utf-8")
        demos.append({
            "id": demoId,
            "title": demo["title"],
            "mood": demo["mood"],
            "imageName": demo["image"],
            "audioUrl": f"/artifacts/demo/audio/{clip.name}",
            "imageUrl": f"/artifacts/demo/images/{image.name}",
            "videoUrl": f"/artifacts/demo/{video.name}",
            "posterUrl": f"/artifacts/demo/{poster.name}",
            "analysisUrl": f"/artifacts/demo/analysis/{demoId}.json",
            "tempo": analysis["tempo"],
            "durationSeconds": analysis["durationSeconds"],
            "segmentStart": analysis["segmentStart"],
            "syncScore": analysis["syncScore"],
        })
        print(f"  {analysis['durationSeconds']} s · {analysis['tempo']} BPM · sincronía {analysis['syncScore']}")

    manifest = {"name": "Ritmo de Luz", "bands": 12, "fps": 30, "credits": CREDITS, "demos": demos}
    (demoDir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
