"""Version-aware pass profiles, saved outside the installed add-on."""

import json
import os
from pathlib import Path
import tempfile

import bpy
from .setup import LIBRARIES, engine_name


def _profile_path(engine):
    directory = Path(bpy.utils.user_resource("CONFIG", path="exr2nuke", create=True))
    return directory / f"{engine}_fast_select.json"


def _defaults(engine):
    return json.loads((LIBRARIES / f"{engine}_fast_select.json").read_text(encoding="utf-8"))


def _parent(layer, path):
    return {
        "view_layer": layer,
        "view_layer.cycles": getattr(layer, "cycles", None),
        "view_layer.eevee": getattr(layer, "eevee", None),
    }.get(path)


def apply(context=None):
    context = context or bpy.context
    engine = engine_name(context.scene)
    defaults = _defaults(engine)
    path = _profile_path(engine)
    profile = json.loads(path.read_text(encoding="utf-8")) if path.exists() else defaults
    if not isinstance(profile, dict):
        raise ValueError("Invalid pass profile. Remove the saved profile to restore defaults.")
    updates = []
    for key, definition in defaults.items():
        parent = _parent(context.view_layer, definition["parent"])
        attribute = definition["attribute"]
        if parent is None or not hasattr(parent, attribute):
            continue
        entry = profile.get(key, definition)
        if not isinstance(entry, dict) or "value" not in entry:
            raise ValueError("Invalid pass profile value.")
        value = entry["value"]
        if type(value) is not type(definition["value"]):
            raise ValueError("Invalid pass profile value type.")
        updates.append((parent, attribute, value, getattr(parent, attribute)))
    try:
        for parent, attribute, value, _old in updates:
            setattr(parent, attribute, value)
    except Exception:
        for parent, attribute, _value, old in updates:
            setattr(parent, attribute, old)
        raise
    context.view_layer.update_render_passes()


def save(context=None):
    context = context or bpy.context
    engine = engine_name(context.scene)
    profile = _defaults(engine)
    for entry in profile.values():
        parent = _parent(context.view_layer, entry["parent"])
        if parent is not None and hasattr(parent, entry["attribute"]):
            entry["value"] = getattr(parent, entry["attribute"])
    path = _profile_path(engine)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(profile, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return path
