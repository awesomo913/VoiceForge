import json
from params import VoiceParams, DSPParams, AIEnhanceParams, RVCParams


def test_default_construction():
    p = VoiceParams()
    assert p.dsp.pitch_semitones == 0.0
    assert p.dsp.formant_shift == 0.0
    assert p.enhance.enabled is True
    assert p.rvc.enabled is False


def test_round_trip_json():
    p = VoiceParams()
    p.dsp.pitch_semitones = -3.0
    p.dsp.clarity = 75.0
    p.rvc.enabled = True
    p.rvc.index_rate = 0.5
    restored = VoiceParams.from_json(p.to_json())
    assert restored.dsp.pitch_semitones == -3.0
    assert restored.dsp.clarity == 75.0
    assert restored.rvc.enabled is True
    assert restored.rvc.index_rate == 0.5


def test_from_partial_dict():
    # from_dict must tolerate missing keys (use defaults)
    p = VoiceParams.from_dict({"dsp": {"pitch_semitones": 5.0}})
    assert p.dsp.pitch_semitones == 5.0
    assert p.dsp.clarity == 0.0  # defaulted
