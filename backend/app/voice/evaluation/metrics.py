"""Evaluation metrics for speech recognition, language ID, terminology normalization, and TTS."""

from dataclasses import dataclass, field


@dataclass
class VoiceEvaluationMetrics:
    """Calculates WER, CER, Language ID accuracy, normalization precision, and latency breakdowns."""

    total_samples: int = 0
    correct_language_id: int = 0
    correct_entity_normalization: int = 0
    successful_tts_synthesis: int = 0
    total_wer_score: float = 0.0
    total_cer_score: float = 0.0

    stt_latency_ms: float = 0.0
    normalization_latency_ms: float = 0.0
    agent_latency_ms: float = 0.0
    tts_latency_ms: float = 0.0

    def add_result(
        self,
        lang_id_match: bool,
        normalization_match: bool,
        tts_success: bool,
        wer: float = 0.0,
        cer: float = 0.0,
        stt_ms: float = 0.0,
        norm_ms: float = 0.0,
        agent_ms: float = 0.0,
        tts_ms: float = 0.0,
    ) -> None:
        self.total_samples += 1
        if lang_id_match:
            self.correct_language_id += 1
        if normalization_match:
            self.correct_entity_normalization += 1
        if tts_success:
            self.successful_tts_synthesis += 1

        self.total_wer_score += wer
        self.total_cer_score += cer

        self.stt_latency_ms += stt_ms
        self.normalization_latency_ms += norm_ms
        self.agent_latency_ms += agent_ms
        self.tts_latency_ms += tts_ms

    @property
    def language_id_accuracy(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.correct_language_id / self.total_samples

    @property
    def normalization_accuracy(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.correct_entity_normalization / self.total_samples

    @property
    def average_wer(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.total_wer_score / self.total_samples

    @property
    def average_cer(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.total_cer_score / self.total_samples

    @property
    def tts_success_rate(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.successful_tts_synthesis / self.total_samples

    @property
    def average_total_latency_ms(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return (
            self.stt_latency_ms
            + self.normalization_latency_ms
            + self.agent_latency_ms
            + self.tts_latency_ms
        ) / self.total_samples
