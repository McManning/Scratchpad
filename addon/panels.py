
import os
import bpy
import numpy as np
from bgl import *

from bpy.types import Panel

from .engine import FooRenderEngine

class BasePanel(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    COMPAT_ENGINES = {FooRenderEngine.bl_idname}

    @classmethod
    def poll(cls, context):
        return context.engine in cls.COMPAT_ENGINES

class FOO_RENDER_PT_settings(BasePanel):
    """Parent panel for renderer settings"""
    bl_label = 'Foo Renderer Settings'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        settings = context.scene.foo
        # No controls at top level.
        
class FOO_RENDER_PT_settings_viewport(BasePanel):
    """Global viewport configurations"""
    bl_label = 'Viewport'
    bl_parent_id = 'FOO_RENDER_PT_settings'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        settings = context.scene.foo

        col = layout.column(align=True)
        col.prop(settings, 'clear_color')
        col.prop(settings, 'ambient_color')

class FOO_RENDER_PT_settings_shader(BasePanel):
    """Shader configurations and reload settings"""
    bl_label = 'Shader'
    bl_parent_id = 'FOO_RENDER_PT_settings'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        settings = context.scene.foo

        col = layout.column(align=True)
        col.prop(settings, 'loader')

        # Render dynamic properties if provided by the current shader
        if hasattr(context.scene, 'foo_dynamic'):
            layout.separator()
            col = layout.column(align=True)

            props = context.scene.foo_dynamic
            # Annotations are used here because this is how we added *Property instances
            # TODO: Support grouping in some way 
            for name in props.__annotations__.keys():
                col.prop(props, name)

        layout.separator()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(settings, "live_reload", text="Live Reload")
        row.operator("foo.reload_sources", text="Reload")
        
        # col = layout.column(align=True)
        # col.alignment = 'RIGHT'
        # col.label(text="Last reloaded N minutes ago")
        
        # Alert message and trace on compile errors
        col = layout.column(align=True)
        col.alert = True

        if settings.last_shader_error:
            col.label(text='Compilation error(s):', icon='ERROR')
            lines = settings.last_shader_error.split('\n')
            for line in lines:
                col.label(text=line)

class FOO_LIGHT_PT_light(BasePanel):
    """Custom per-light settings editor for this render engine"""
    bl_label = 'Light'
    bl_context = 'data'
    
    @classmethod
    def poll(cls, context):
        return context.light and BasePanel.poll(context)

    def draw(self, context):
        layout = self.layout
        light = context.light
        
        settings = context.light.foo
        
        if self.bl_space_type == 'PROPERTIES':
            layout.row().prop(light, 'type', expand=True)
            layout.use_property_split = True
        else:
            layout.use_property_split = True
            layout.row().prop(light, 'type')
        
        col = layout.column()
        col.prop(light, 'color')
        
        col.separator()
        col.prop(settings, 'distance')
        col.prop(settings, 'intensity')
        
        if light.type == 'SPOT':
            col.prop(light, 'spot_size')
            col.prop(light, 'spot_blend')
            
class FOO_PT_context_material(BasePanel):
    """This is based on CYCLES_PT_context_material to provide the same material selector menu"""
    bl_label = ''
    bl_context = 'material'
    bl_options = {'HIDE_HEADER'}

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type == 'GPENCIL':
            return False
       
        return (context.material or context.object) and BasePanel.poll(context)

    def draw(self, context):
        layout = self.layout

        mat = context.material
        ob = context.object
        slot = context.material_slot
        space = context.space_data

        if ob:
            is_sortable = len(ob.material_slots) > 1
            rows = 1
            if (is_sortable):
                rows = 4

            row = layout.row()

            row.template_list("MATERIAL_UL_matslots", "", ob, "material_slots", ob, "active_material_index", rows=rows)

            col = row.column(align=True)
            col.operator("object.material_slot_add", icon='ADD', text="")
            col.operator("object.material_slot_remove", icon='REMOVE', text="")

            col.menu("MATERIAL_MT_context_menu", icon='DOWNARROW_HLT', text="")

            if is_sortable:
                col.separator()

                col.operator("object.material_slot_move", icon='TRIA_UP', text="").direction = 'UP'
                col.operator("object.material_slot_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

            if ob.mode == 'EDIT':
                row = layout.row(align=True)
                row.operator("object.material_slot_assign", text="Assign")
                row.operator("object.material_slot_select", text="Select")
                row.operator("object.material_slot_deselect", text="Deselect")

        split = layout.split(factor=0.65)

        if ob:
            split.template_ID(ob, "active_material", new="material.new")
            row = split.row()

            if slot:
                row.prop(slot, "link", text="")
            else:
                row.label()
        elif mat:
            split.template_ID(space, "pin_id")
            split.separator()

class FOO_MATERIAL_PT_settings(BasePanel):
    bl_label = 'Settings'
    bl_context = 'material'
    
    @classmethod 
    def poll(cls, context):   
        return context.material and BasePanel.poll(context)

    def draw(self, context):
        mat = context.material 
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.label(text='TODO: Anything common?')

class FOO_MATERIAL_PT_settings_dynamic(BasePanel):
    """Dynamic per-shader properties added to a material"""
    bl_label = 'Shader Properties'
    bl_parent_id = 'FOO_MATERIAL_PT_settings'

    def draw(self, context):
        mat = context.material
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        settings = context.scene.foo
        
        col = layout.column()
        
        if settings.last_shader_error:
            col.label(text='Resolve shader errors to see additional properties')
        elif not hasattr(mat, 'foo_dynamic'):
            col.label(text='No additional properties for the current shader')
        else:
            props = mat.foo_dynamic
            # Annotations are used here because this is how we added *Property instances
            # TODO: Support grouping in some way 
            for name in props.__annotations__.keys():
                col.prop(props, name)

classes = (
    # Renderer panels
    FOO_RENDER_PT_settings,
    FOO_RENDER_PT_settings_viewport,
    FOO_RENDER_PT_settings_shader,

    # Light panels
    FOO_LIGHT_PT_light,

    # Material panels
    FOO_PT_context_material,
    FOO_MATERIAL_PT_settings,
    FOO_MATERIAL_PT_settings_dynamic
)
