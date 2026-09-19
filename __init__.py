# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright Lucas Rouge and Adrien Blanchard.
# This program is free software under GNU GPL version 2 or any later version.
# It is distributed without warranty; see LICENSE for the complete terms.
"""Exr2Nuke: grouped multilayer EXR output for Blender compositing."""

bl_info = {
    "name": "Exr2Nuke",
    "author": "Lucas Rouge, Adrien Blanchard",
    "description": "Render-pass outputs for compositing in Nuke",
    "blender": (3, 6, 0),
    "version": (1, 1, 0),
    "location": "Properties > View Layer > Exr2Nuke",
    "doc_url": "https://github.com/adrien-blanchard/exr2nuke",
    "tracker_url": "https://github.com/adrien-blanchard/exr2nuke/issues",
    "category": "Render",
}

import bpy
from .modules import Fast_selection
from .modules.setup import compositor_tree, create_setup, engine_name, OWNER


class EXR2NUKE_OT_generate(bpy.types.Operator):
    bl_idname = "exr2nuke.generate"
    bl_label = "Generate EXR outputs"
    bl_description = "Replace only Exr2Nuke-managed nodes; keep your other compositor nodes"
    bl_options = {"REGISTER", "UNDO"}
    count: bpy.props.IntProperty(default=1, min=1, max=3)

    def execute(self, context):
        try:
            outputs = create_setup(self.count, context)
        except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Generated {len(outputs)} EXR output(s).")
        return {"FINISHED"}


class EXR2NUKE_OT_profile(bpy.types.Operator):
    bl_idname = "exr2nuke.profile"
    bl_label = "Pass profile"
    bl_options = {"REGISTER", "UNDO"}
    save_profile: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        try:
            if self.save_profile:
                Fast_selection.save(context)
            else:
                Fast_selection.apply(context)
        except (ValueError, RuntimeError, OSError, TypeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report(
            {"INFO"},
            "Pass profile saved." if self.save_profile else "Pass profile applied.",
        )
        return {"FINISHED"}


class EXR2NUKE_PT_panel(bpy.types.Panel):
    bl_label = "Exr2Nuke"
    bl_idname = "EXR2NUKE_PT_panel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "view_layer"

    def draw(self, context):
        layout = self.layout
        try:
            engine = engine_name(context.scene)
        except ValueError:
            layout.label(text="Choose Cycles or Eevee.", icon="INFO")
            return
        row = layout.row(align=True)
        row.operator("exr2nuke.profile", text="Apply profile", icon="PRESET").save_profile = False
        row.operator("exr2nuke.profile", text="Save profile", icon="FILE_TICK").save_profile = True
        if engine == "Cycles":
            layout.prop(
                context.view_layer.cycles,
                "denoising_store_passes",
                text="Denoise light passes",
            )
        layout.separator()
        layout.label(text="Output grouping")
        for count, label in [
            (1, "1  All passes"),
            (2, "2  Light + Data / Cryptomatte"),
            (3, "3  Light / Data / Cryptomatte"),
        ]:
            layout.operator("exr2nuke.generate", text=label, icon="NODE").count = count
        layout.label(text="Regenerate after changing passes.", icon="INFO")
        tree = compositor_tree(context.scene)
        if tree:
            for node in tree.nodes:
                if node.get(OWNER) and node.bl_idname == "CompositorNodeOutputFile":
                    box = layout.box()
                    box.label(text=node.get("exr2nuke_output", node.label))
                    if hasattr(node, "directory"):
                        box.prop(node, "directory", text="")
                        box.prop(node, "file_name", text="Name")
                    else:
                        box.prop(node, "base_path", text="")


CLASSES = (EXR2NUKE_OT_generate, EXR2NUKE_OT_profile, EXR2NUKE_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
