import json
from dataclasses import asdict, dataclass, field


@dataclass
class DSPParams:
    pitch_semitones: float = 0.0
    formant_shift: float = 0.0
    clarity: float = 0.0
    warmth: float = 0.0
    reverb_room: float = 0.0
    reverb_damping: float = 0.5
    reverb_wet: float = 0.0
    echo_delay_ms: float = 200.0
    echo_feedback: float = 0.0
    echo_wet: float = 0.0
    deesser_freq: float = 7000.0
    deesser_threshold_db: float = -80.0
    gate_threshold_db: float = -60.0
    gate_attack_ms: float = 10.0
    gate_release_ms: float = 100.0
    vibrato_rate_hz: float = 5.0
    vibrato_depth: float = 0.0


@dataclass
class AIEnhanceParams:
    enabled: bool = True
    noise_suppression: float = 50.0
    voice_restoration: float = 50.0


@dataclass
class RVCParams:
    enabled: bool = False
    model_path: str = ""
    index_path: str = ""
    pitch_offset: float = 0.0
    index_rate: float = 0.75
    filter_radius: int = 3
    rms_mix_rate: float = 0.25
    protect_rate: float = 0.33
    f0_method: str = "rmvpe"


@dataclass
class VoiceParams:
    dsp: DSPParams = field(default_factory=DSPParams)
    enhance: AIEnhanceParams = field(default_factory=AIEnhanceParams)
    rvc: RVCParams = field(default_factory=RVCParams)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "VoiceParams":
        dsp_data = d.get("dsp", {})
        enhance_data = d.get("enhance", {})
        rvc_data = d.get("rvc", {})
        dsp_fields = {f for f in DSPParams.__dataclass_fields__}
        enhance_fields = {f for f in AIEnhanceParams.__dataclass_fields__}
        rvc_fields = {f for f in RVCParams.__dataclass_fields__}
        return cls(
            dsp=DSPParams(**{k: v for k, v in dsp_data.items() if k in dsp_fields}),
            enhance=AIEnhanceParams(
                **{k: v for k, v in enhance_data.items() if k in enhance_fields}
            ),
            rvc=RVCParams(**{k: v for k, v in rvc_data.items() if k in rvc_fields}),
        )

    @classmethod
    def from_json(cls, s: str) -> "VoiceParams":
        return cls.from_dict(json.loads(s))
