
# Contributing

Pull requests are welcome for new features and bug fixes. I'm pretty new to low level render engine work so contributions are very welcome.

The overall goal is to keep the engine as simple as possible and just expose what's needed for shader programs to do custom drawing in the viewport. 

## Running Tests

Run `python -m unittest discover test`

Tests currently ignore modules that depend on Blender modules (bpy, bgl, etc)
