
from .lights import (
    MainLight
)

class LightData:
    """Current scene lighting information provided to shaders and passes"""
    def __init__(self):
        self.main_light = MainLight() 
        self.additional_lights = {}

class ShadowData:
    def __init__(self):
        pass

class CameraData:
    def __init__(self):
        self.view_matrix = None
        self.projection_matrix = None 

class RenderData:
    def __init__(self):
        self.lights = LightData()
        self.shadows = ShadowData()
        self.camera = CameraData()
        self.renderables = {}  # ScratchpadMaterial -> Renderable[]  
    
    def clear(self):
        self.lights.additional_lights = {}
        self.renderables = {}
    
