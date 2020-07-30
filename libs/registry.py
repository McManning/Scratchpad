import bpy 
from .debug import debug

class Registry:
    """Manager for a set of classes to (un)register with bpy"""
    classes = []

    def __call__(self, cls):
        Registry.add(cls)

    @classmethod
    def add(cls, instance):
        cls.classes.append(instance)
    
    @classmethod
    def register(cls):
        for c in cls.classes:
            debug('[Autoregister] Register {}'.format(c))
            bpy.utils.register_class(c)
            
            # If registering a RenderEngine, notify panels
            if issubclass(c, bpy.types.RenderEngine):
                name = c.bl_idname
                for panel in get_panels(c.exclude_panels):
                    debug('[Autoregister] Register {} to Panel {}'.format(
                        name,
                        panel
                    ))
                    panel.COMPAT_ENGINES.add(name)

    @classmethod 
    def unregister(cls):
        render_engine_id = None

        for c in reversed(cls.classes):
            debug('[Autoregister] Unregister {}'.format(c))
            bpy.utils.unregister_class(c)

            # If unregistering a RenderEngine, notify panels
            if issubclass(c, bpy.types.RenderEngine):
                name = c.bl_idname
                for panel in get_panels([]):
                    if name in panel.COMPAT_ENGINES:
                        debug('[Autoregister] Unregister {} from Panel {}'.format(
                            name,
                            panel
                        ))
                        panel.COMPAT_ENGINES.remove(name)

        # Unregister dynamic-generated property groups 
        if hasattr(bpy, 'scratchpad_dynamic_registry'):
            for key, instance in bpy.scratchpad_dynamic_registry.items():
                try:
                    bpy.utils.unregister_class(instance)
                except: 
                    pass
                
            bpy.scratchpad_dynamic_registry = {}

    @classmethod
    def clear(cls):
        cls.classes = []

    @classmethod
    def register_dynamic(cls, name: str, instance):
        if not hasattr(bpy, 'scratchpad_dynamic_registry'):
            bpy.scratchpad_dynamic_registry = {}

        bpy.utils.register_class(instance)
        bpy.scratchpad_dynamic_registry[name] = instance

    @classmethod
    def unregister_dynamic(cls, name: str):
        if hasattr(bpy, 'scratchpad_dynamic_registry') and name in bpy.scratchpad_dynamic_registry:
            instance = bpy.scratchpad_dynamic_registry[name]
            debug('Unregister dynamic', instance)

            try:
                bpy.utils.unregister_class(instance)
            except: 
                pass
            
            del bpy.scratchpad_dynamic_registry[name]
        else:
            debug('Cannot find dynamic to unregister:', name)

def autoregister(cls):
    """Decorator to automatically add a class to the registry when imported"""
    Registry.add(cls)
    return cls

def get_panels(exclude_panels):
    """UI Panels that the RenderEngine is compatible with
    
    Properties:
        exclude_panels (list[str]): Panel names to not register the RenderEngine with
    """
    # Ref: https://docs.blender.org/api/current/bpy.types.RenderEngine.html
    panels = []
    for panel in bpy.types.Panel.__subclasses__():
        if hasattr(panel, 'COMPAT_ENGINES') and 'BLENDER_RENDER' in panel.COMPAT_ENGINES:
            if panel.__name__ not in exclude_panels:
                panels.append(panel)

    return panels

