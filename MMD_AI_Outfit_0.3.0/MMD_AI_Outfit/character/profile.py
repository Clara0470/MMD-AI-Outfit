"""Persistent Character Profile data helpers."""

from datetime import datetime, timezone
import json


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_profile(armature_name):
    return {
        "schema_version": 1,
        "character": {"armature": armature_name},
        "skeleton": {"status": "pending", "unit": "BU", "measured_at": None, "measurements": {}},
        "body_shape": {"status": "pending", "mesh": None, "unit": "BU", "measured_at": None, "measurements": {}},
    }


def load_profile(raw, armature_name, legacy_skeleton=""):
    """Load a profile, migrating the former flat measurement JSON when present."""
    profile = None
    if raw:
        try:
            candidate = json.loads(raw)
            if isinstance(candidate, dict) and candidate.get("schema_version"):
                profile = candidate
        except (TypeError, ValueError):
            pass
    if profile is None:
        profile = new_profile(armature_name)
        if legacy_skeleton:
            try:
                values = json.loads(legacy_skeleton)
                if isinstance(values, dict):
                    profile["skeleton"].update(
                        status="measured", measured_at=None, measurements=values
                    )
            except (TypeError, ValueError):
                pass
    profile.setdefault("schema_version", 1)
    profile.setdefault("character", {})["armature"] = armature_name
    profile.setdefault("skeleton", {"status": "pending", "unit": "BU", "measured_at": None, "measurements": {}})
    profile.setdefault("body_shape", {"status": "pending", "mesh": None, "unit": "BU", "measured_at": None, "measurements": {}})
    return profile


def record_skeleton(profile, measurements):
    profile["skeleton"] = {
        "status": "measured",
        "unit": "BU",
        "measured_at": _now(),
        "measurements": measurements,
    }
    return profile


def record_body_shape(profile, mesh_name, measurements):
    profile["body_shape"] = {
        "status": "measured",
        "mesh": mesh_name,
        "unit": "BU",
        "measured_at": _now(),
        "measurements": measurements,
    }
    return profile


def serialize_profile(profile):
    return json.dumps(profile, ensure_ascii=False, separators=(",", ":"))
