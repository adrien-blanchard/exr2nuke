"""Run with blender --background --factory-startup --python-exit-code 1 --python tests/blender_smoke.py."""

import importlib.util
from pathlib import Path
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
scene.name = "Not the default scene"
scene.render.engine = "CYCLES"
with tempfile.TemporaryDirectory(prefix="exr2nuke-test-") as directory:
    addon.Fast_selection._profile_path = lambda engine: Path(directory) / (engine + ".json")
    addon.Fast_selection.apply()
    addon.Fast_selection.save()
    layer = bpy.context.view_layer
    for family in ("diffuse", "glossy", "transmission"):
        for component in ("direct", "indirect", "color"):
            setattr(layer, f"use_pass_{family}_{component}", True)
    layer.use_pass_emit = layer.use_pass_environment = True
    layer.cycles.use_pass_volume_direct = layer.cycles.use_pass_volume_indirect = True
    lighting = {
        "DiffDir",
        "DiffInd",
        "DiffCol",
        "GlossDir",
        "GlossInd",
        "GlossCol",
        "TransDir",
        "TransInd",
        "TransCol",
        "VolDir",
        "VolInd",
        "Emit",
        "Env",
    }
    tree = addon.compositor_tree(scene, create=True)
    artist_node = tree.nodes.new("CompositorNodeRGB")
    artist_node.name = "Artist node - preserve me"
    for count in (1, 2, 3, 1):
        outputs = addon.create_setup(count)
        assert len(outputs) == count, (count, outputs.keys())
        assert tree.nodes.get(artist_node.name) == artist_node
        assert all(node.format.file_format == "OPEN_EXR_MULTILAYER" for node in outputs.values())
        assert all(any(socket.is_linked for socket in node.inputs) for node in outputs.values())
        light_node = outputs[{1: "File_Output_exr", 2: "Light_Data_exr", 3: "Light_exr"}[count]]
        linked = {socket.name for socket in light_node.inputs if socket.is_linked}
        assert lighting <= linked, ("Missing lighting", lighting - linked)
        for name in ("Data_exr", "Cryptomatte_exr"):
            if name in outputs:
                assert not lighting.intersection(socket.name for socket in outputs[name].inputs)
        assert (
            len(
                [
                    node
                    for node in tree.nodes
                    if node.get(addon.OWNER) and node.bl_idname == "CompositorNodeRLayers"
                ]
            )
            == 1
        )
        for node in tree.nodes:
            if node.get(addon.OWNER) and node.bl_idname == "CompositorNodeDenoise":
                assert node.inputs["Normal"].links[0].from_socket.name == "Denoising Normal"
                assert node.inputs["Albedo"].links[0].from_socket.name == "Denoising Albedo"
    node = next(iter(outputs.values()))
    path_attr = "directory" if hasattr(node, "directory") else "base_path"
    setattr(node, path_attr, "//artist-custom-output/")
    outputs = addon.create_setup(1)
    assert getattr(next(iter(outputs.values())), path_attr) == "//artist-custom-output/"
    before = len(tree.nodes)
    try:
        addon.create_setup(0)
        raise AssertionError("Invalid grouping accepted")
    except ValueError:
        assert len(tree.nodes) == before
    engines = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    scene.render.engine = (
        "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    )
    addon.Fast_selection.apply()
    layer.use_pass_diffuse_color = True
    outputs = addon.create_setup(2)
    linked = {socket.name for socket in outputs["Light_Data_exr"].inputs if socket.is_linked}
    assert {"DiffLight", "DiffCol", "GlossLight", "GlossCol", "emit", "env"} <= linked, linked
    assert not any(
        node.bl_idname == "CompositorNodeDenoise" for node in tree.nodes if node.get(addon.OWNER)
    )
addon.unregister()
addon.register()
addon.unregister()
print("EXR2NUKE_SMOKE_OK", bpy.app.version_string)
