
if 'bpy' in locals():
    import importlib
    importlib.reload(bgl_driver)
else:
    from . import bgl_driver
    

import bpy

# TODO: Something less... gross? 
# I'm doing this so I can just do a `import CommandBuffer from driver`
# and not worry about which implementation is used.  

class Graphics(bgl_driver.Graphics):
    pass 

class CommandBuffer(bgl_driver.CommandBuffer):
    pass
