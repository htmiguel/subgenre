from __future__ import annotations

from pathlib import Path
from typing import Any


def analyze_local(path: Path) -> dict[str, Any] | None:
    """
    Local EchoNest-ish proxies: tempo (BPM) and key estimate via librosa.
    Returns None if librosa is not installed or analysis fails.
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        return None

    path = path.resolve()
    try:
        y, sr = librosa.load(str(path), sr=None, mono=True, duration=120.0)
    except Exception:
        return None
    if y.size == 0:
        return None

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo_arr = librosa.beat.tempo(onset_envelope=onset_env, sr=sr, aggregate=np.median)
    tempo = float(tempo_arr[0]) if tempo_arr is not None and len(tempo_arr) else None

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    major = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    maj_corr = float(np.corrcoef(major, chroma_mean)[0, 1])
    min_corr = float(np.corrcoef(minor, chroma_mean)[0, 1])
    if np.isnan(maj_corr):
        maj_corr = 0.0
    if np.isnan(min_corr):
        min_corr = 0.0
    idx = int(np.argmax(chroma_mean))
    ks = key_names[idx]
    if maj_corr >= min_corr:
        key_str = f"{ks} major"
    else:
        key_str = f"{ks} minor"

    # Simple spectral "energy" proxy (0–1 scaled)
    rms = librosa.feature.rms(y=y)[0]
    energy_proxy = float(np.clip(np.mean(rms) * 8.0, 0.0, 1.0))

    out: dict[str, Any] = {
        "tempo": tempo,
        "key": key_str,
        "energy_proxy": energy_proxy,
        "source": "librosa",
    }
    return out
