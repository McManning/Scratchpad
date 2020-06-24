
from bgl import *
from mathutils import Vector
from math import cos

class SceneLighting:
    """Current scene lighting information provided to shaders"""
    def __init__(self):
        self.ambient_color = (0, 0, 0)
        self.main_light = None 
        self.additional_lights = dict()


class MainLight:
    """Primary directional light"""
    def __init__(self):
        # self.position = (0, 0, 0, 1)
        self.direction = (0, 0, 1, 0)
        self.color = (1, 1, 1, 1)

    def update(self, obj):
        settings = obj.data.foo
        
        # Object data
        direction = obj.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        color = obj.data.color

        self.direction = (direction[0], direction[1], direction[2], 0)
        self.color = (color[0], color[1], color[2], settings.intensity)
        

class SpotLight:
    def __init__(self):
        self.position = (0, 0, 0, 1)
        self.direction = (0, 1, 0, 0)
        self.color = (1, 1, 1, 1)
        self.attenuation = (0, 1, 0, 1)

    def update(self, obj):
        settings = obj.data.foo
        
        # Object data
        position = obj.matrix_world.to_translation()
        direction = obj.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        color = obj.data.color

        # Convert spot size and blend (factor) to inner/outer angles
        spot_angle = obj.data.spot_size
        inner_spot_angle = obj.data.spot_size * (1.0 - obj.data.spot_blend)

        # Vec4s that match Unity's URP for forward lights
        self.position = (position[0], position[1], position[2], 1.0)
        self.direction = (direction[0], direction[1], direction[2], 0)
        self.color = (color[0], color[1], color[2], settings.intensity)
        
        # Range and attenuation settings
        light_range_sqr = settings.distance * settings.distance # TODO: Should be scale or something, so it matches the gizmo 
        fade_start_distance_sqr = 0.8 * 0.8 * light_range_sqr
        fade_range_sqr = fade_start_distance_sqr - light_range_sqr

        self.attenuation = (1.0 / light_range_sqr, -light_range_sqr / fade_range_sqr, 0, 1)

        light_range_sqr = settings.distance * settings.distance # TODO: Should be scale or something, so it matches the gizmo 
        fade_start_distance_sqr = 0.8 * 0.8 * light_range_sqr
        fade_range_sqr = fade_start_distance_sqr - light_range_sqr

        cos_outer_angle = cos(spot_angle * 0.5)
        cos_inner_angle = cos(inner_spot_angle * 0.5)
        smooth_angle_range = max(0.001, cos_inner_angle - cos_outer_angle)
        inv_angle_range = 1.0 / smooth_angle_range
        add = -cos_outer_angle * inv_angle_range

        self.attenuation = (1.0 / light_range_sqr, -light_range_sqr / fade_range_sqr, inv_angle_range, add)


class PointLight:
    def __init__(self):
        self.position = (0, 0, 0, 1)
        self.direction = (0, 1, 0, 0)
        self.color = (1, 1, 1, 1)
        self.attenuation = (0, 1, 0, 1)

    def update(self, obj):
        settings = obj.data.foo
        
        # Object data
        position = obj.matrix_world.to_translation()
        direction = obj.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        color = obj.data.color
        
        # Vec4s that match Unity's URP for forward lights
        self.position = (position[0], position[1], position[2], 1.0)
        self.direction = (direction[0], direction[1], direction[2], 0)
        self.color = (color[0], color[1], color[2], settings.intensity)
        
        # Range and attenuation settings
        light_range_sqr = settings.distance * settings.distance
        fade_start_distance_sqr = 0.8 * 0.8 * light_range_sqr
        fade_range_sqr = fade_start_distance_sqr - light_range_sqr

        self.attenuation = (1.0 / light_range_sqr, -light_range_sqr / fade_range_sqr, 0, 1)
