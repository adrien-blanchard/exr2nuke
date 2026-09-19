"""Build a managed compositor setup without deleting the artist's nodes.

Copyright Lucas Rouge and Adrien Blanchard. GPL-2.0-or-later.
The original 2023 pass libraries are retained; Blender 5's compositor API is
adapted here alongside the legacy API.
"""

import json
from pathlib import Path

import bpy

OWNER = "exr2nuke_managed"
LIBRARIES = Path(__file__).resolve().parent.parent / "libraries"


def engine_name(scene):
    if scene.render.engine == "CYCLES":
        return "Cycles"
    if scene.render.engine in {"BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"}:
        return "Eevee"
    raise ValueError("Choose Cycles or Eevee before generating outputs.")


def compositor_tree(scene, create=False):
    if hasattr(scene, "compositing_node_group"):
        if create and scene.compositing_node_group is None:
            scene.compositing_node_group = bpy.data.node_groups.new(
                f"{scene.name} - Exr2Nuke", "CompositorNodeTree"
            )
        return scene.compositing_node_group
    if create:
        scene.use_nodes = True
    return scene.node_tree


def output_groups(count):
    if count == 1:
        return {"File_Output_exr": {"Light", "Data", "Crypto"}}
    if count == 2:
        return {"Light_Data_exr": {"Light", "Data"}, "Cryptomatte_exr": {"Crypto"}}
    if count == 3:
        return {
            "Light_exr": {"Light"},
            "Data_exr": {"Data"},
            "Cryptomatte_exr": {"Crypto"},
        }
    raise ValueError("Output count must be 1, 2 or 3.")


def _output_path(node):
    if hasattr(node, "directory"):
        return (node.directory, node.file_name)
    return node.base_path


def _configure_output(node, name, stem, previous):
    node.format.file_format = "OPEN_EXR_MULTILAYER"
    node.format.color_depth = "32"
    node.format.exr_codec = "ZIP"
    node.use_custom_color = True
    node.color = (0.36, 0.23, 0.40)
    if hasattr(node, "file_output_items"):
        node.file_output_items.clear()
        node.directory = f"//Render/{name}/"
        node.file_name = f"{stem}_####"
        if isinstance(previous, tuple):
            node.directory, node.file_name = previous
    else:
        node.file_slots.clear()
        node.base_path = (
            previous if isinstance(previous, str) else f"//Render/{name}/{stem}_####.exr"
        )


def _add_slot(node, name, socket_type):
    if hasattr(node, "file_output_items"):
        item_type = {"RGBA": "RGBA", "VECTOR": "VECTOR", "VALUE": "FLOAT"}.get(socket_type, "RGBA")
        node.file_output_items.new(item_type, name)
        return node.inputs[name]
    return node.file_slots.new(name)


def create_setup(count, context=None):
    context = context or bpy.context
    scene, layer = context.scene, context.view_layer
    engine = engine_name(scene)
    groups = output_groups(count)
    library = json.loads((LIBRARIES / f"{engine}_Node_Library.json").read_text(encoding="utf-8"))
    layer.update_render_passes()
    tree = compositor_tree(scene, create=True)
    old_nodes = [node for node in tree.nodes if node.get(OWNER)]
    old_paths = {
        node.get("exr2nuke_output"): _output_path(node)
        for node in old_nodes
        if node.bl_idname == "CompositorNodeOutputFile"
    }
    created = []

    def new(kind, label):
        node = tree.nodes.new(kind)
        created.append(node)
        node[OWNER] = True
        node.label = label
        return node

    try:
        render = new("CompositorNodeRLayers", "Exr2Nuke - Render Layers")
        render.scene = scene
        render.layer = layer.name
        render.location = (0, 0)
        useful = [
            (socket, library[socket.name])
            for socket in render.outputs
            if socket.enabled and socket.name in library
        ]
        if not useful:
            raise ValueError("Enable at least one supported render pass first.")
        denoise = engine == "Cycles" and layer.cycles.denoising_store_passes
        normal = render.outputs.get("Denoising Normal")
        albedo = render.outputs.get("Denoising Albedo")
        denoise = denoise and normal is not None and albedo is not None
        stem = Path(bpy.data.filepath).stem or "untitled"
        outputs = {}
        for index, (name, categories) in enumerate(groups.items()):
            passes = [
                (socket, info) for socket, info in useful if categories.intersection(info["out"])
            ]
            if not passes:
                continue
            node = new("CompositorNodeOutputFile", name)
            node["exr2nuke_output"] = name
            node.location = (800, -index * 350)
            _configure_output(node, name, stem, old_paths.get(name))
            outputs[name] = node
        denoisers = {}
        for socket, info in useful:
            source = socket
            if denoise and info["denoise"]:
                node = new("CompositorNodeDenoise", "Denoise - " + info["name"])
                node.location = (400, -len(denoisers) * 50)
                node.hide = True
                tree.links.new(socket, node.inputs["Image"])
                tree.links.new(normal, node.inputs["Normal"])
                tree.links.new(albedo, node.inputs["Albedo"])
                source = node.outputs["Image"]
                denoisers[socket.name] = node
            for name, node in outputs.items():
                if groups[name].intersection(info["out"]):
                    target = _add_slot(node, info["name"], socket.type)
                    tree.links.new(source, target)
        for node in old_nodes:
            tree.nodes.remove(node)
        for name, node in outputs.items():
            node.name = name
        return outputs
    except Exception:
        for node in reversed(created):
            tree.nodes.remove(node)
        raise
