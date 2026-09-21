import numpy as np
import pytest
from ritmo_de_luz_core import (
    analyzeAudio,
    bandCell,
    buildMosaicFrame,
    clusterStates,
    extractPalette,
    pickSegment,
    renderVideo,
)
from ritmo_de_luz_core.audio import attackRelease, percentileNormalize

SR = 22050


def clicks(seconds: float = 4.0, every: float = 0.5) -> np.ndarray:
    """Tono grave continuo más golpes agudos periódicos: onsets conocidos."""
    t = np.arange(int(seconds * SR)) / SR
    signal = 0.2 * np.sin(2 * np.pi * 80 * t)
    for start in np.arange(0.25, seconds, every):
        i = int(start * SR)
        burst = np.random.default_rng(int(start * 100)).normal(0, 0.8, 800) * np.hanning(800)
        signal[i:i + 800] += burst
    return signal.astype(np.float32)


def test_features_are_12_mel_bands_normalized_and_aligned():
    features = analyzeAudio(clicks(), SR)
    assert features.melSmooth.shape[0] == 12
    n = features.times.size
    for series in (features.melRaw, features.melSmooth):
        assert series.shape == (12, n)
        assert series.min() >= 0 and series.max() <= 1
    assert features.rms.shape == features.onset.shape == features.flash.shape == (n,)
    # Límites mel crecientes y espaciado no lineal (más estrecho en graves).
    edges = features.bandEdgesHz
    assert np.all(np.diff(edges) > 0) and np.diff(edges)[0] < np.diff(edges)[-1]


def test_onsets_are_detected_near_the_clicks():
    features = analyzeAudio(clicks(), SR)
    expected = np.arange(0.25, 4.0, 0.5)
    hits = [np.min(np.abs(features.onsetTimes - t)) < 0.05 for t in expected]
    assert np.mean(hits) >= 0.8
    assert features.flash.max() > 0.3


def test_percentile_normalization_ignores_one_outlier():
    values = np.r_[np.linspace(0, 1, 99), 100.0]
    normalized = percentileNormalize(values)
    assert normalized[50] > 0.4  # un pico aislado no aplasta el resto a 0


def test_attack_release_rises_fast_and_falls_slow():
    step = np.r_[np.zeros(5), np.ones(5), np.zeros(10)]
    smooth = attackRelease(step, 0.6, 0.08)
    assert smooth[5] >= 0.6  # sube en un hop
    assert smooth[11] > 0.8  # tras apagarse aún conserva energía
    assert np.all(np.diff(smooth[10:]) <= 0)


def test_band_layout_bass_bottom_left_treble_top_right():
    assert bandCell(0) == (2, 0)
    assert bandCell(3) == (2, 3)
    assert bandCell(11) == (0, 3)


def test_mosaic_tiles_show_their_own_region_and_react():
    base = np.zeros((72, 128, 3), dtype=np.uint8)
    base[:, :64] = (200, 40, 40)  # mitad izquierda roja
    base[:, 64:] = (40, 40, 200)  # mitad derecha azul
    quiet = buildMosaicFrame(base, np.zeros(12), gutter=2).astype(float)
    loud = buildMosaicFrame(base, np.ones(12), gutter=2).astype(float)
    assert quiet.shape == (72, 128, 3)
    # El mosaico de la columna 0 conserva el rojo de su región; el de la columna 3, el azul.
    assert loud[40, 10, 0] > loud[40, 10, 2] and loud[40, 120, 2] > loud[40, 120, 0]
    assert loud.mean() > quiet.mean() * 2
    with pytest.raises(ValueError):
        buildMosaicFrame(base, np.zeros(6))


def test_palette_and_states_are_ordered():
    pixels = np.array([(250, 30, 30)] * 50 + [(30, 30, 30)] * 50, dtype=np.uint8).reshape(10, 10, 3)
    palette = extractPalette(pixels, colors=2)
    assert len(palette.colors) == 2 and abs(sum(palette.weights) - 1) < 1e-6
    features = analyzeAudio(clicks(), SR)
    states, labels = clusterStates(features, palette)
    assert labels.shape == features.rms.shape
    energies = [state.energy for state in states]
    assert energies == sorted(energies)
    assert states[-1].color == palette.byVividness()[-1]  # estado más enérgico → color más vivo


def test_pick_segment_prefers_the_loud_part():
    signal = np.r_[np.zeros(SR * 10), np.ones(SR * 5) * 0.5, np.zeros(SR * 10)].astype(np.float32)
    start, segment = pickSegment(signal, SR, seconds=6)
    assert 4 <= start <= 10.5 and segment.size == SR * 6


def test_render_video_writes_mp4_and_analysis(tmp_path):
    image = np.zeros((90, 160, 3), dtype=np.uint8)
    image[..., 1] = 160
    output = tmp_path / "out.mp4"
    analysis = renderVideo(image, clicks(3.0), output, sampleRate=SR, minSeconds=0, fps=10,
                           size=(160, 96), posterPath=tmp_path / "poster.jpg")
    assert output.stat().st_size > 0 and (tmp_path / "poster.jpg").exists()
    assert len(analysis["frames"]["bands"]) == 30 and len(analysis["frames"]["bands"][0]) == 12
    assert analysis["syncScore"] > 0.3


def test_short_audio_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="al menos 10"):
        renderVideo(np.zeros((20, 20, 3), dtype=np.uint8), np.zeros(SR), tmp_path / "x.mp4", sampleRate=SR)
