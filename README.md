# Foo Render Engine (Final Name Pending)

Custom GLSL Render Engines for Blender 2.8+

This project contains a full render engine implementation and a single .py micro engine.

## Requirements

* Blender 2.8+
* Probably Windows (see Limitations)

## Features

* Full GLSL pipeline - including Geometry and Tessellation shaders
* Support for #include directives
* Hot reloading of shader source files when changed on disk
* (Some) support for Maya's OGSFX shader format

## Limitations

Because this is a pure Python render engine, you will start to notice slowdown when you hit a large number of faces (e.g. 1 million) especially when trying to sculpt. It's suggested that you keep the polycount to a minimum, or toggling between standard viewport and the shader viewport when working with higher polycounts. 

No shadow support because I'm bad at that (pull requests very welcome)

Lighting is limited to one directional light and up to 16 point lights. Other lights (area) are not supported.

No per-material shaders (...yet)

There is no integration with Blender's shader nodes, nor is it planned.

Tested on Windows 10. YMMV on OSX.

# Micro Engine

A standalone micro version of the library is included as `micro.py`. 

If you are looking for a simple base for building your own render engine, or want to do something more Shadertoy-esque in Blender, try this instead of the full addon.

## Features

* Full GLSL pipeline - including Geometry and Tessellation shaders
* Hot reloading of shader source files when changed on disk


# Contributing

Pull requests are welcome for new features and bug fixes. 

## Running Tests

Run `python -m unittest discover test`

Tests currently ignore modules that depend on Blender modules (bpy, bgl, etc)
