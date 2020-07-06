import bpy 

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
            print('[Autoregister] Register {}'.format(c))
            bpy.utils.register_class(c)

    @classmethod 
    def unregister(cls):
        for c in reversed(cls.classes):
            print('[Autoregister] Unregister {}'.format(c))
            bpy.utils.unregister_class(c)

    @classmethod
    def clear(cls):
        cls.classes = []

def autoregister(cls):
    """Decorator to automatically add a class to the registry when imported"""
    Registry.add(cls)
