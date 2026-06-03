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


def test_from_empty_dict():
    p = VoiceParams.from_dict({})
    assert p.dsp.pitch_semitones == 0.0
    assert p.enhance.enabled is True
    assert p.rvc.enabled is False


def test_from_dict_ignores_extra_keys():
    p = VoiceParams.from_dict({
        "dsp": {"pitch_semitones": 2.0, "unknown_field": "ignored"},
        "unknown_top_level": "also_ignored"
    })
    assert p.dsp.pitch_semitones == 2.0
    assert p.dsp.clarity == 0.0  # defaulted


def test_from_dict_all_missing_subdicts():
    p = VoiceParams.from_dict({"dsp": {}, "enhance": {}, "rvc": {}})
    assert p.dsp.pitch_semitones == 0.0
    assert p.enhance.noise_suppression == 50.0
    assert p.rvc.index_rate == 0.75
