"""Voice effect presets for real-time voice changing.

Provides Voicemod-style voice presets like Robot, Chipmunk, Deep Voice, etc.
"""

from __future__ import annotations

from app.realtime.effects_processor import EffectParameters


# ==============================================================================
# Voice Effect Presets
# ==============================================================================

VOICE_PRESETS = {
    "none": {
        "name": "None (Bypass)",
        "description": "No effects applied - original voice",
        "icon": "🔇",
        "params": EffectParameters(
            # All effects disabled
        ),
    },
    "robot": {
        "name": "Robot",
        "description": "Metallic robotic voice with distortion",
        "icon": "🤖",
        "params": EffectParameters(
            pitch_shift=-3.0,
            formant_shift=0.8,
            distortion_enabled=True,
            distortion_gain=8.0,
            distortion_mix=0.6,
            chorus_enabled=True,
            chorus_rate=5.0,
            chorus_depth=0.015,
            chorus_mix=0.4,
            eq_enabled=True,
            eq_low_gain=-3.0,
            eq_mid_gain=2.0,
            eq_high_gain=4.0,
        ),
    },
    "chipmunk": {
        "name": "Chipmunk",
        "description": "High-pitched squeaky voice",
        "icon": "🐿️",
        "params": EffectParameters(
            pitch_shift=8.0,
            formant_shift=1.6,
            eq_enabled=True,
            eq_low_gain=-6.0,
            eq_mid_gain=0.0,
            eq_high_gain=3.0,
        ),
    },
    "deep_voice": {
        "name": "Deep Voice",
        "description": "Deep, bass-heavy voice",
        "icon": "🎙️",
        "params": EffectParameters(
            pitch_shift=-6.0,
            formant_shift=0.6,
            eq_enabled=True,
            eq_low_gain=6.0,
            eq_mid_gain=-2.0,
            eq_high_gain=-4.0,
            reverb_enabled=True,
            reverb_room_size=0.3,
            reverb_damping=0.7,
            reverb_wet=0.2,
        ),
    },
    "monster": {
        "name": "Monster",
        "description": "Terrifying monster voice",
        "icon": "👹",
        "params": EffectParameters(
            pitch_shift=-10.0,
            formant_shift=0.5,
            distortion_enabled=True,
            distortion_gain=12.0,
            distortion_mix=0.5,
            reverb_enabled=True,
            reverb_room_size=0.7,
            reverb_damping=0.4,
            reverb_wet=0.4,
            eq_enabled=True,
            eq_low_gain=8.0,
            eq_mid_gain=-3.0,
            eq_high_gain=-6.0,
        ),
    },
    "radio": {
        "name": "Radio",
        "description": "Old radio transmission effect",
        "icon": "📻",
        "params": EffectParameters(
            distortion_enabled=True,
            distortion_gain=3.0,
            distortion_mix=0.3,
            eq_enabled=True,
            eq_low_gain=-8.0,
            eq_mid_gain=4.0,
            eq_high_gain=-8.0,
            noise_gate_enabled=True,
            noise_gate_threshold=-35.0,
        ),
    },
    "cave": {
        "name": "Cave",
        "description": "Large cave reverb",
        "icon": "🏔️",
        "params": EffectParameters(
            pitch_shift=-2.0,
            reverb_enabled=True,
            reverb_room_size=0.9,
            reverb_damping=0.3,
            reverb_wet=0.6,
            delay_enabled=True,
            delay_time=0.15,
            delay_feedback=0.3,
            delay_mix=0.3,
            eq_enabled=True,
            eq_low_gain=2.0,
            eq_mid_gain=-1.0,
            eq_high_gain=-3.0,
        ),
    },
    "telephone": {
        "name": "Telephone",
        "description": "Phone call quality",
        "icon": "☎️",
        "params": EffectParameters(
            eq_enabled=True,
            eq_low_gain=-10.0,
            eq_mid_gain=5.0,
            eq_high_gain=-10.0,
            distortion_enabled=True,
            distortion_gain=2.0,
            distortion_mix=0.2,
        ),
    },
    "alien": {
        "name": "Alien",
        "description": "Extraterrestrial voice",
        "icon": "👽",
        "params": EffectParameters(
            pitch_shift=4.0,
            formant_shift=1.3,
            chorus_enabled=True,
            chorus_rate=3.0,
            chorus_depth=0.03,
            chorus_mix=0.5,
            reverb_enabled=True,
            reverb_room_size=0.5,
            reverb_wet=0.3,
            eq_enabled=True,
            eq_low_gain=-2.0,
            eq_mid_gain=3.0,
            eq_high_gain=5.0,
        ),
    },
    "echo_chamber": {
        "name": "Echo Chamber",
        "description": "Strong echo effect",
        "icon": "🔊",
        "params": EffectParameters(
            delay_enabled=True,
            delay_time=0.4,
            delay_feedback=0.6,
            delay_mix=0.5,
            reverb_enabled=True,
            reverb_room_size=0.6,
            reverb_wet=0.3,
        ),
    },
    "helium": {
        "name": "Helium",
        "description": "Like inhaling helium gas",
        "icon": "🎈",
        "params": EffectParameters(
            pitch_shift=10.0,
            formant_shift=1.8,
            eq_enabled=True,
            eq_low_gain=-8.0,
            eq_mid_gain=1.0,
            eq_high_gain=4.0,
        ),
    },
    "demon": {
        "name": "Demon",
        "description": "Demonic voice from hell",
        "icon": "😈",
        "params": EffectParameters(
            pitch_shift=-12.0,
            formant_shift=0.4,
            distortion_enabled=True,
            distortion_gain=15.0,
            distortion_mix=0.7,
            reverb_enabled=True,
            reverb_room_size=0.8,
            reverb_damping=0.2,
            reverb_wet=0.5,
            eq_enabled=True,
            eq_low_gain=10.0,
            eq_mid_gain=-4.0,
            eq_high_gain=-8.0,
        ),
    },
}


def get_preset(preset_id: str) -> dict:
    """Get preset by ID.

    Args:
        preset_id: Preset identifier

    Returns:
        Preset dictionary with name, description, icon, and params

    Raises:
        KeyError: If preset not found
    """
    if preset_id not in VOICE_PRESETS:
        raise KeyError(f"Preset '{preset_id}' not found")

    return VOICE_PRESETS[preset_id]


def get_preset_parameters(preset_id: str) -> EffectParameters:
    """Get effect parameters for a preset.

    Args:
        preset_id: Preset identifier

    Returns:
        Effect parameters

    Raises:
        KeyError: If preset not found
    """
    preset = get_preset(preset_id)
    return preset["params"]


def list_presets() -> list[dict]:
    """Get list of all available presets.

    Returns:
        List of preset info (id, name, description, icon)
    """
    presets = []
    for preset_id, preset_data in VOICE_PRESETS.items():
        presets.append({
            "id": preset_id,
            "name": preset_data["name"],
            "description": preset_data["description"],
            "icon": preset_data["icon"],
        })

    return presets
