# Foo Render Engine (Final Name Pending)

Pure Python render engine for Blender 2.8+. 

This addon allows a developer to write realtime viewport shaders as GLSL code with as much access to the render pipeline as possible.

The Github project contains both the full render engine addon and a simplified `micro.py` standalone version.

## Requirements

* Blender 2.8+
* Probably Windows (see Limitations)

## Features

* Full GLSL pipeline - including Geometry and Tessellation shaders
* Support for #include directives
* Hot reloading of shader source files when changed on disk

## Planned Features

* (Some) support for Maya's OGSFX shader format and other external formats
* Dynamic property editors from shader annotations
* Multiple shader passes
* Compute-based pipelines - e.g. running a custom compute tessellator before passing data off to the standard stages

## Limitations

Because this is a pure Python render engine, you will start to notice slowdown when you hit a large number of faces (e.g. 1 million) especially when trying to sculpt. It's suggested that you keep the polycount to a minimum, or toggling between standard viewport and the shader viewport when working with higher polycounts. 

No shadow support because I'm bad at that (pull requests very welcome)

Lighting is limited to one directional light and up to 16 point lights. Other lights (area) are not supported.

No per-material shaders (...yet)

There is no integration with Blender's shader nodes, nor is it a design goal. 

Tested on Windows 10. YMMV on other platforms. 

# Micro Engine

A standalone micro version of the library is included as `micro.py` with a reduced set of features.

If you are looking for a simple base to build your own render engine, or want to do something more Shadertoy-esque in Blender, try this instead of the full addon.
