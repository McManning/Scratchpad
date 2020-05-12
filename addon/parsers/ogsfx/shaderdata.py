"""
Common structured data generated from different shader formats
"""

from typing import List

class Annotation:
    """User editable metadata for a uniform, technique, or pass
    
    string UIWidget = "None";
    int UISomething("Notes", Range(0, 1)) = 5;

    TODO: description/ui_specifier is not applicable for OGSFX.
    Mixed it up with ShaderLab
    """
    type_specifier: str # string, int, float
    name: str
    description: str # Optional
    ui_specifier: tuple # Optional
    # value # "myStr", 1, 2.0, (x,y,z), True/False, etc
    
    def __init__(self):
        self.ui_specifier = (None,)
        self.value = None

    def __repr__(self):
        return '<Annotation({}), type={}, value={}, desc={}, ui={}>'.format(
            self.name,
            self.type_specifier,
            self.value,
            self.description,
            self.ui_specifier
        )

class Uniform:
    """ 
    uniform gMVP : WorldViewProjection < ... > = constant;
    """
    type_specifier: str # float, mat4, sampler2D
    name: str
    alias: str # : WorldViewProjection
    annotations: List[Annotation]
    # value # 5.0f, Vector3(...), SamplerState

    def __init__(self):
        self.alias = None
        self.annotations = []
        self.value = None

    def __repr__(self):
        return '<Uniform({}), type={}, alias={}, value={}, annotations={}>'.format(
            self.name,
            self.type_specifier,
            self.alias,
            self.value,
            self.annotations
        )

# TODO: "Varying" isn't quite accurate here.
# Attribute is, but it could be a non-varying
# input attribute to the vertex shader.
class VaryingAttribute:
    """
    vec4 position : POSITION;
    """
    type_specifier: str # float, mat4, vec3
    name: str
    input_specifier: str # POSITION, NORMAL, TEXCOORD0

    def __repr__(self):
        return '<Varying({}), type={}, in={}>'.format(
            self.name,
            self.type_specifier,
            self.input_specifier
        )

class VertexStream:
    """Set of attributes for stage IO
    attribute APPDATA {
        ...
    };
    """
    name: str
    attributes: List[VaryingAttribute]

    def __repr__(self):
        return '<VertexStream({}), decl={}>'.format(
            self.name,
            self.declarations
        )

class GLSLSource: # TODO: Rename GLSLCode ?
    """
    GLSLShader foo {
        ...
    }
    """
    name: str
    code: str 

    def __init__(self, name: str, code: str):
        self.name = name
        self.code = code 
    
    def __repr__(self):
        return '<GLSLSource({})>'.format(self.name)

class StageArgument:
    """
    in APPDATA vsin
    in APPDATA
    """
    type_qualifier: str # in/out
    attribute_name: str
    name: str # optional
    
    def __repr__(self):
        return self.name

class Stage:
    """
    VertexShader(in APPDATA vsin, out V2F vsout) = { Foo, Bar }
    VertexShader (in appdata, out brixVertexOutput) = VS;
    """
    name: str # "VertexShader", "PixelShader", etc 
    in_arg: StageArgument
    out_arg: StageArgument
    shader_ids: List[str]

    def __init__(self):
        self.shader_ids = []

    def __repr__(self):
        return '<Stage({}), in={}, out={}, sources={}>'.format(
            self.name,
            self.in_arg,
            self.out_arg,
            self.shader_ids
        )
        
class Pass:
    """
    pass p0 < ... > {
        ...
    }
    """
    name: str
    annotations: List[Annotation]
    stages: List[Stage]

    def __init__(self, name: str):
        self.name = name
        self.annotations = []
    
    def __repr__(self):
        return '<Pass({}), stages={}, annotations={}>'.format(
            self.name,
            self.stages,
            self.annotations
        )

    def find_stage(self, name: str) -> Stage:
        for stage in self.stages:
            if stage.name == name:
                return stage 
        return None

class Technique:
    """
    technique Main < ... > {
        ...
    }
    """
    name: str
    annotations: List[Annotation]
    passes: List[Pass]
    
    def __init__(self, name: str):
        self.name = name
        self.annotations = []
        self.passes = []
    
    def __repr__(self):
        return '<Technique({}), passes={}, annotations={}>'.format(
            self.name,
            self.passes,
            self.annotations
        )

class SamplerState:
    """
    sampler_state {
        Texture = <gMyTex>;
    };
    """
    name: str

    def __repr__(self):
        return '<SamplerState({})>'.format(self.name)

class OGSFXShader:
    name = 'Maya OGSFX'

    uniforms: List[Uniform]
    attributes: List[VertexStream]
    techniques: List[Technique]
    glsl: List[GLSLSource]
    defines: dict

    active_technique: str

    def __init__(self):
        self.uniforms = []
        self.attributes = []
        self.techniques = []
        self.glsl = []
        self.defines = {
            'DEBUG': '1'
        }

    def __repr__(self):
        return '<OGSFX uniforms={}, attributes={}, techniques={}>'.format(
            self.uniforms,
            self.attributes,
            self.techniques
        )
    
    def set_blocks(self, blocks: List):
        for block in blocks:
            if type(block) == Uniform:
                self.uniforms.append(block)
            elif type(block) == VertexStream:
                self.attributes.append(block)
            elif type(block) == Technique:
                self.techniques.append(block)
            elif type(block) == GLSLSource:
                self.glsl.append(block)
            else:
                raise Exception('Unhandled block type {}'.format(
                    type(block)
                ))
    
    def get_uniforms_as_glsl(self):
        code = ''
    
        # inject uniforms
        for uniform in self.uniforms:
            code += 'uniform {} {};\n'.format(
                uniform.type_specifier,
                uniform.name
            )
            
        return code 

    def get_defines_as_glsl(self) -> str:
        code = ''
        for key, value in self.defines.items():
            code += '#define {} {}\n'.format(
                key,
                value or ''
            )
        
        return code
        
    def get_stage_argument_as_glsl(self, arg: StageArgument) -> str:
        qualifier = arg.type_qualifier 
        vs = self.find_vertex_stream(arg.attribute_name)
        shader = ''
        if not arg.name:
            # No struct, expose each attribute as direct
            for attr in vs.attributes:
                shader += '{} {} {};\n'.format(
                    qualifier,
                    attr.type_specifier,
                    attr.name
                )
        else:
            # As an interface block. This does not work for 
            # inputs to VS - as those cannot be wrapped.
            # TODO: Detect named VS inputs and handle?
            shader += '{} {} {{\n'.format(qualifier, arg.attribute_name)
            for attr in vs.attributes:
                shader += '    {} {};\n'.format(
                    attr.type_specifier, 
                    attr.name
                )
            shader += '}} {};\n'.format(arg.name)
        
        return shader
    
    def get_glsl(self, technique_name: str, stage_name: str) -> dict:
        """Return runnable GLSL code for the given technique+stage combo
        
        :return dict: mapping pass name to code (str)
        """
        passes = {}
        technique = self.find_technique(technique_name)
        uniforms = self.get_uniforms_as_glsl()
        defines = self.get_defines_as_glsl()

        # Inject GLSL code blocks associated with the pass
        for pss in technique.passes:            
            stage = pss.find_stage(stage_name)
            if stage:
                shader = '#version 420 core\n'
                shader += defines
                shader += uniforms

                # Convert IO args into GLSL
                shader += self.get_stage_argument_as_glsl(stage.in_arg)
                shader += self.get_stage_argument_as_glsl(stage.out_arg)
                
                # Concatenate sources onto each other
                # (do I need to add a #line directive for this?)
                # Parser should probably add one at the top of
                # each source.
                for name in stage.shader_ids:
                    glsl = self.find_glsl_source(name)
                    shader += glsl.code

                passes[pss.name] = shader
            else:
                passes[pss.name] = None
            
        return passes

    def find_glsl_source(self, name: str):
        for glsl in self.glsl:
            if glsl.name == name:
                return glsl 

        raise Exception('No GLSLShader named {}'.format(name))
    
    def find_vertex_stream(self, name: str):
        for attr in self.attributes:
            if attr.name == name:
                return attr 

        raise Exception('No attribute named {}'.format(name))
    
    def find_technique(self, name: str) -> Technique:
        for tech in self.techniques:
            if tech.name == name:
                return tech 

        raise Exception('No technique named {}'.format(name))

    def find_uniforms(self, alias: str) -> List[Uniform]:
        """Retrieve all declared uniforms with the alias"""
        return [u for u in self.uniforms if u.alias == alias]
    
    def find_attributes(self, input_specifier: str) -> List[VaryingAttribute]:
        """Retrieve all VS attributes with the given input specifier"""
        return [a for a in self.attributes if a.input_specifier == input_specifier]
    
    """
    the theory is:

    bind VBO 
    pos = get_attributes_with_input_specifier('POSITION')
    for p in pos:
        apply to buffer

    Alternatively, bind:
    __position
    And then (somewhere...) set a uniform to it. 
    Can we do that? Doesn't seem like it tho.

    uniforms = get_uniforms_with_alias('WorldViewProjection')
    for u in uniforms:
        shader.set_vec4(u, mvp)
    etc.

    I need the Shader at this point.
    What else is needed? Pass support - need GLSL

    Annotation integration.. somehow?
    """

    def get_config_settings(self):
        config = ShaderConfig()
        
        for u in self.uniforms:
            group = 'Settings' # Default group
            setting = ShaderConfigSetting()

            # TODO: Figure it out based on uniform type
            settings.input_type = ShaderConfigSetting.FLOAT

            for a in u.annotations:
                if a.name == 'UIName':
                    setting.name = str(a.value)
                elif a.name == 'UIMin':
                    setting.input_type = ShaderConfigSetting.RANGE
                    setting.range_min = int(a.value)
                elif a.name == 'UIMax':
                    setting.input_type = ShaderConfigSetting.RANGE
                    setting.range_max = int(a.value)
                elif a.name == 'UIGroup':
                    group = str(a.value)
                elif a.name == 'UIOrder':
                    setting.order= int(a.value)
                elif a.name == 'UIWidget':
                    # TODO: Widget customization
                elif a.name == 'UIFieldNames':
                    setting.input_type = ShaderConfigSetting.DROPDOWN
                    setting.set_options(str(a.value))
                # ... and so on ...
            
            # Assume UIName is set to expose an editor
            if settings.name:
                config.add_setting(group, setting)

class ShaderConfigSetting:
    FLOAT = 1,
    RANGE = 2,
    COLOR = 3
    DROPDOWN = 4

    order: int
    input_type: int
    range_min: int
    range_max: int

    # Map an ID to a string
    options: dict

    def __init__(self):
        self.value = None
        self.default_value = None
    #... how does arbitrary persistence work in blender?

    def set_options(self, format: str):
        """Convert an enum string to an options dict"""

        """
        UIFieldNames = "Shaded:Wireframe=8:Bounding Box"
        dropdown, Shaded is 0, Wireframe is 8, Bounding Box is 9
        """

class ShaderConfig:
    # Map title to list of settings
    groups: dict

    def __init__(self):
        self.groups = {}

    def add_setting(group: str, setting: ShaderConfigSetting):
        if group not in self.groups:
            self.groups[group] = []
        
        self.groups[group].append(setting)

    def sort():
        # TODO: Sort all settings
        pass
    