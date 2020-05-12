
import os 
from typing import List
from ply import yacc 

from .lexer import tokens
from .shaderdata import * 

# First rule is starting symbol
def p_shader(p):
    '''shader : block_list'''
    shader = OGSFXShader()
    shader.set_blocks(p[1])
    p[0] = shader

def p_block_list(p):
    '''block_list   : block
                    | block_list block'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_block_glsl(p):
    '''block : GLSL'''
    name, code = p[1]
    p[0] = GLSLSource(name, code)

def p_block(p):
    '''block    : technique
                | uniform
                | attribute_struct'''
    p[0] = p[1] # attribute, uniform, preprocessor?

def p_technique(p):
    'technique : TECHNIQUE ID annotations_opt LBRACE pass_list RBRACE'
    t = Technique(name=p[2])
    t.annotations = p[3]
    t.passes = p[5]
    p[0] = t

def p_pass(p):
    'pass : PASS ID annotations_opt LBRACE stage_list RBRACE'
    a = Pass(name=p[2])
    a.annotations = p[3]
    a.stages = p[5]
    p[0] = a

def p_pass_list(p):
    '''pass_list    : pass
                    | pass_list pass'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_id_list(p):
    '''id_list  : ID
                | id_list COMMA ID'''
    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]

def p_shader_id_list(p):
    '''shader_id_list   : ID
                        | LBRACE id_list RBRACE'''
    p[0] = [p[1]] if len(p) == 2 else p[2]

def p_stage_name(p):
    '''stage_name   : VERTEXSHADER
                    | TESSCONTROLSHADER
                    | TESSEVALSHADER
                    | GEOMETRYSHADER
                    | PIXELSHADER'''
    stage = Stage()
    stage.name = p[1]
    p[0] = stage

def p_stage_argument(p):
    '''stage_argument   : IN ID ID
                        | OUT ID ID'''
    arg = StageArgument()
    arg.type_qualifier = p[1]
    arg.attribute_name = p[2]
    arg.name = p[3]
    p[0] = arg

def p_stage_argument_untyped(p):
    '''stage_argument   : IN ID
                        | OUT ID'''
    arg = StageArgument()
    arg.type_qualifier = p[1]
    arg.attribute_name = p[2]
    arg.name = None
    p[0] = arg 
    
def p_stage(p):
    'stage : stage_name LPAREN stage_argument COMMA stage_argument RPAREN EQ shader_id_list SEMI'
    stage = p[1]
    stage.in_arg = p[3]
    stage.out_arg = p[5]
    stage.shader_ids = p[8]
    p[0] = stage

def p_stage_list(p):
    '''stage_list   : stage
                    | stage_list stage'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_empty(p):
    'empty :'
    pass

def p_type_specifier(p):
    '''type_specifier   : FLOAT 
                        | INT
                        | VEC2
                        | VEC3
                        | VEC4
                        | MAT3
                        | MAT4
                        | TEXTURE2D
                        | SAMPLER2D'''
    p[0] = p[1] # Type was already created by the lexer

def p_number(p):
    '''number   : INT_CONST
                | FLOAT_CONST'''
    p[0] = p[1]

def p_constant_vec2(p):
    'constant_vec2 : LBRACE number COMMA number RBRACE'
    p[0] = (p[2], p[4])

def p_constant_vec3(p):
    'constant_vec3 : LBRACE number COMMA number COMMA number RBRACE'
    p[0] = (p[2], p[4], p[6])

def p_constant_vec4(p):
    'constant_vec4 : LBRACE number COMMA number COMMA number COMMA number RBRACE'
    p[0] = (p[2], p[4], p[6], p[8])

def p_sampler_state(p):
    'sampler_state : SAMPLER_STATE LBRACE TEXTURE EQ LT ID GT SEMI RBRACE'
    ss = SamplerState()
    ss.name = p[6]
    p[0] = ss

def p_constant(p):
    '''constant : number
                | constant_vec2
                | constant_vec3
                | constant_vec4
                | sampler_state'''
    p[0] = p[1]

def p_annotation_constant(p):
    '''annotation_constant : number
                            | STRING_CONST
                            | BOOL_CONST
                            | constant_vec2
                            | constant_vec3
                            | constant_vec4'''
                            # TODO: Are constant vecs right?
    p[0] = p[1]

def p_uniform(p):
    '''uniform  : UNIFORM type_specifier ID annotations_opt SEMI
                | UNIFORM type_specifier ID annotations_opt EQ constant SEMI'''
    u = Uniform()
    u.type_specifier = p[2]
    u.name = p[3]
    u.annotations = p[4]
    u.value = p[6] if len(p) > 6 else None
    p[0] = u

def p_uniform_with_alias(p):
    '''uniform  : UNIFORM type_specifier ID COLON ID SEMI
                | UNIFORM type_specifier ID COLON ID EQ constant SEMI'''
    u = Uniform()
    u.type_specifier = p[2]
    u.name = p[3]
    u.alias = p[5]
    u.value = p[7] if len(p) > 7 else None
    p[0] = u

def p_input_specifier(p):
    '''input_specifier  : POSITION
                        | NORMAL 
                        | TANGENT 
                        | BINORMAL
                        | COLOR0 
                        | TEXCOORD0 
                        | TEXCOORD1 
                        | TEXCOORD2 
                        | TEXCOORD3 
                        | TEXCOORD4 
                        | TEXCOORD5 
                        | TEXCOORD6 
                        | TEXCOORD7'''
    p[0] = p[1]

def p_attribute(p):
    'attribute : type_specifier ID COLON input_specifier SEMI'
    v = VaryingAttribute()
    v.type_specifier = p[1]
    v.name = p[2]
    v.input_specifier = p[4]
    p[0] = v

def p_attribute_list(p):
    '''attribute_list   : attribute
                        | attribute_list attribute'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_attribute_list_opt(p):
    '''attribute_list_opt   : attribute_list
                            | empty'''
    p[0] = p[1]
    
def p_attribute_struct(p):
    'attribute_struct : ATTRIBUTE ID LBRACE attribute_list_opt RBRACE SEMI'
    s = VertexStream()
    s.name = p[2]
    s.attributes = p[4]
    p[0] = s

def p_annotation_type_specifier(p):
    '''annotation_type_specifier    : STRING
                                    | INT
                                    | FLOAT
                                    | BOOL'''
    p[0] = p[1]

def p_annotation(p):
    'annotation : annotation_type_specifier ID annotation_args_opt EQ annotation_constant SEMI'
    a = Annotation()
    description, ui_specifier = p[3]

    a.type_specifier = p[1]
    a.name = p[2]
    a.description = description 
    a.ui_specifier = ui_specifier
    a.value = p[5]
    p[0] = a

def p_annotation_no_const(p):
    'annotation : annotation_type_specifier ID annotation_args_opt SEMI'
    a = Annotation()
    description, ui_specifier = p[3]

    a.type_specifier = p[1]
    a.name = p[2]
    a.description = description 
    a.ui_specifier = ui_specifier
    a.value = None
    p[0] = a

def p_annotation_list(p):
    '''annotation_list  : annotation
                        | annotation_list annotation'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_annotations_opt(p):
    '''annotations_opt  : empty
                        | LT annotation_list GT'''
    p[0] = p[2] if len(p) > 2 else []

def p_annotation_ui_specifier(p):
    'annotation_ui_specifier : COLOR'
    p[0] = (p[1],) # TODO: Maybe not tuples here.

def p_annotation_ui_specifier_range(p):
    'annotation_ui_specifier : RANGE LPAREN number COMMA number RPAREN'
    p[0] = ('Range', p[3], p[5])

def p_annotation_args(p):
    'annotation_args : LPAREN STRING_CONST RPAREN'
    p[0] = (p[2], None)

def p_annotation_args_with_ui_modifier(p):
    'annotation_args : LPAREN STRING_CONST COMMA annotation_ui_specifier RPAREN'
    p[0] = (p[2], p[4])

def p_annotation_args_opt(p):
    'annotation_args_opt  : annotation_args'
    p[0] = p[1]

def p_annotations_args_opt_empty(p):
    'annotation_args_opt : empty'
    p[0] = ('', None)

def p_error(p):
    print('Parsing error')
    print(p)

    if not p:
        print('End of File!')
        return

    for i in range(0, 10):
        tok = parser.token()
        if not tok: break 
        print(tok.value)

# Build the parser
parser = yacc.yacc()
