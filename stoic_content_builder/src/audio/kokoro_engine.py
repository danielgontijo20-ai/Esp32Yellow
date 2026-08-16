"""Motor Kokoro TTS → WAV (24 kHz)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import config


class KokoroEngine:
    """Wrapper fino sobre kokoro.KPipeline."""

    def __init__(
        self,
        voice: str | None = None,
        lang_code: str | None = None,
        repo_id: str | None = None,
        sample_rate: int | None = None,
        speed: float | None = None,
    ) -> None:
        self.voice = voice or config.VOICE
        self.lang_code = lang_code or config.LANG_CODE
        self.repo_id = repo_id or config.REPO_ID
        self.sample_rate = sample_rate or config.SAMPLE_RATE
        self.speed = speed if speed is not None else config.SPEED
        self._pipeline = None

    def _ensure_pipeline(self) -> None:
        if self._pipeline is not None:
            return
        from kokoro import KPipeline

        self._pipeline = KPipeline(
            lang_code=self.lang_code,
            repo_id=self.repo_id,
        )

    def synthesize_to_array(self, text: str) -> Any:
        """Gera áudio float32 mono a partir do texto."""
        import numpy as np

        if not text or not text.strip():
            raise ValueError("Texto vazio — nada para sintetizar.")

        self._ensure_pipeline()
        assert self._pipeline is not None

        chunks: list = []
        for _gs, _ps, audio in self._pipeline(
            text, voice=self.voice, speed=self.speed
        ):
            if audio is None:
                continue
            arr = np.asarray(audio, dtype=np.float32).reshape(-1)
            if arr.size:
                chunks.append(arr)

        if not chunks:
            raise RuntimeError("Kokoro não retornou áudio para o texto informado.")

        return np.concatenate(chunks)

    def synthesize_to_wav(self, text: str, wav_path: Path) -> tuple[Path, float]:
        """Sintetiza e grava WAV. Retorna (caminho, duração_segundos)."""
        import soundfile as sf

        wav_path = Path(wav_path)
        wav_path.parent.mkdir(parents=True, exist_ok=True)

        audio = self.synthesize_to_array(text)
        sf.write(str(wav_path), audio, self.sample_rate)

        duration = float(len(audio)) / float(self.sample_rate)
        return wav_path, duration
