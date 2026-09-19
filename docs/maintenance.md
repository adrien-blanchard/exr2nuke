# Maintenance notes

## 1.1.0 — September 2026

Maintenance release of Lucas Rouge and Adrien Blanchard's 2023 add-on. The original Gumroad download remains linked; this repository does not replace that listing.

- Support Blender 5's compositor node groups and File Output items alongside the older API.
- Connect denoising sockets by name, avoiding normal/albedo ordering differences.
- Use the active scene and view layer, even when they are not called `Scene` or `ViewLayer`.
- Load libraries relative to the installed package on all platforms.
- Replace only tagged Exr2Nuke nodes, after successful generation; retain custom output paths.
- Save pass profiles atomically in the user's Blender configuration. Skip properties removed by Blender and validate profile values before applying them.
- Consolidate the three duplicated output generators and support Undo.

The smoke suite exercises Cycles/Eevee, one/two/three outputs, regeneration, preservation of artist nodes, denoising links, custom paths and registration cycles. A separate tiny Cycles render checks EXR channels and Cryptomatte manifests on disk. Both ran in Blender 5.0.1 and 5.2.0 LTS on Windows.

No licensed Nuke integration run or production-scene benchmark is claimed. Back up your scene; remove obsolete output nodes from an old version yourself if you no longer want them to render. Untagged legacy nodes are deliberately not deleted automatically.

The README artwork is from the original Gumroad listing. The supplied source archive is dated July 2023; repository commits use their actual maintenance dates. Original authorship and GPL-2.0-or-later licensing are retained.
