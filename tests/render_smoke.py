"""Render a tiny real Cycles EXR and validate its on-disk channels/metadata."""

import importlib.util
from pathlib import Path
import struct
import sys
import tempfile

import bpy

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "exr2nuke", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
)
addon = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = addon
spec.loader.exec_module(addon)
addon.register()
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 1
scene.render.resolution_x = 32
scene.render.resolution_y = 32
scene.render.resolution_percentage = 100
layer = bpy.context.view_layer
layer.use_pass_normal = True
layer.use_pass_z = True
layer.use_pass_cryptomatte_object = True
layer.cycles.denoising_store_passes = True


def cstring(stream):
    value = bytearray()
    while True:
        char = stream.read(1)
        if not char:
            raise ValueError("Truncated EXR")
        if char == b"\0":
            return value.decode("utf-8")
        value.extend(char)


with tempfile.TemporaryDirectory(prefix="exr2nuke-render-") as directory:
    outputs = addon.create_setup(1)
    node = next(iter(outputs.values()))
    if hasattr(node, "directory"):
        node.directory = directory
        node.file_name = "smoke_####"
    else:
        node.base_path = str(Path(directory) / "smoke_####.exr")
    bpy.ops.render.render()
    files = list(Path(directory).glob("*.exr"))
    assert len(files) == 1, files
    with files[0].open("rb") as stream:
        assert stream.read(4) == b"\x76\x2f\x31\x01", "Not an OpenEXR file"
        flags = struct.unpack("<I", stream.read(4))[0]
        headers = []
        while name := cstring(stream):
            attributes = {}
            while name:
                kind = cstring(stream)
                size = struct.unpack("<I", stream.read(4))[0]
                assert size < 8 * 1024 * 1024
                attributes[name] = (kind, stream.read(size))
                name = cstring(stream)
            headers.append(attributes)
            if not flags & 4096:  # OpenEXR multipart flag; otherwise one header.
                break
    import io

    names = []
    for attributes in headers:
        channels = io.BytesIO(attributes["channels"][1])
        while name := cstring(channels):
            names.append(name)
            channels.read(16)
    assert any("rgba" in name for name in names), names
    assert any("normal" in name for name in names), names
    assert any("Depth" in name for name in names), names
    assert any("CryptoObject" in name for name in names), names
    assert any(
        name.startswith("cryptomatte/") and name.endswith("/manifest")
        for attributes in headers
        for name in attributes
    ), headers
    print("EXR2NUKE_RENDER_OK", bpy.app.version_string, names)
addon.unregister()
