import math

from ritmo_de_luz_core import (
    analyze,
    analyzeAudio,
    buildMosaicFrame,
    clusterStates,
    extractPalette,
    generateMosaicMp4,
)
from ritmo_de_luz_core.models import AudioFeatures


def test_audio_features_are_normalized_and_typed():
    samples = [math.sin(2 * math.pi * 440 * i / 8000) for i in range(8000)]
    result = analyzeAudio(samples, 8000, frameSize=256, hopSize=128, melBands=4)
    assert len(result.rms) == len(result.times) > 1
    assert all(0 <= x <= 1 for x in result.rms)
    assert len(result.mel_bands[0]) == 4

def test_palette_and_states_have_deterministic_fallback_shape():
    palette = extractPalette([(255, 0, 0)] * 4 + [(0, 0, 255)] * 4, colors=2)
    assert len(palette.colors) == 2
    audio = AudioFeatures((0.0, 0.1), (0.0, 1.0), (0.2, 0.8), (0.0, 1.0))
    states = clusterStates(audio, palette, count=2)
    assert states and all(0 <= state.intensity <= 1 for state in states)

def test_high_level_analysis_builds_frames():
    result = analyze([0.0] * 512, 8000, [(20, 30, 40)])
    assert len(result.frames) == len(result.audio.times)

def test_mosaic_frame_is_4x6_and_audio_reactive():
    import numpy as np
    image = np.full((80, 120, 3), 100, dtype=np.uint8)
    frame = buildMosaicFrame(image, mel=[0.2, 0.8], size=(120, 80))
    assert frame.shape == (80, 120, 3)
    assert frame.dtype == np.uint8

def test_mosaic_mp4_from_arrays(tmp_path):
    import pytest
    pytest.importorskip("imageio.v3")
    import numpy as np
    image = np.zeros((40, 60, 3), dtype=np.uint8); image[:, :, 0] = 180
    output = tmp_path / "visual.mp4"
    generateMosaicMp4(image, np.zeros(800), str(output), sampleRate=8000, fps=4, size=(120, 80))
    assert output.exists() and output.stat().st_size > 0


def test_empty_audio_is_rejected(tmp_path):
    import pytest
    pytest.importorskip("numpy")
    import numpy as np
    with pytest.raises(ValueError, match="at least one sample"):
        generateMosaicMp4(np.zeros((20, 20, 3), dtype=np.uint8), np.array([]), str(tmp_path / "empty.mp4"), sampleRate=8000)
