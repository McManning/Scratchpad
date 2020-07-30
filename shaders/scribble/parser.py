
import os 
from libs.ply import yacc
from .lexer import tokens
from .shader import *

# First rule is starting symbol
def p_shader(p):
    '''shader : SHADER LBRACE block_list RBRACE'''
    shader = ScribbleShader(p[3])
    shader.name = 'default'
    p[0] = shader

def p_block_list(p):
    '''block_list   : block
                    | block_list block'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_block_glsl(p):
    '''block : GLSL'''
    name, code = p[1]
    glsl = GLSLSource()
    glsl.name = name
    glsl.code = code
    glsl.lineno = p.lineno(1)
    p[0] = glsl

def p_block_technique(p):
    '''block : technique'''
    p[0] = p[1]

def p_block_properties(p):
    '''block : properties'''
    p[0] = p[1]

def p_technique(p):
    'technique : TECHNIQUE ID LBRACE pass_list RBRACE'
    t = Technique()
    t.name = p[2]
    t.passes = p[4]
    p[0] = t

def p_pass(p):
    'pass : PASS LBRACE stage_list RBRACE'
    a = Pass()
    a.stages = p[3]
    p[0] = a

def p_pass_list(p):
    '''pass_list    : pass
                    | pass_list pass'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_id_list(p):
    '''id_list  : ID
                | id_list COMMA ID'''
    p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]

def p_one_or_more_ids(p):
    '''one_or_more_ids  : ID
                        | LPAREN id_list RPAREN'''
    p[0] = [p[1]] if len(p) == 2 else p[2]

def p_stage_name(p):
    '''stage_name   : VERTEXSHADER
                    | TESSCONTROLSHADER
                    | TESSEVALSHADER
                    | GEOMETRYSHADER
                    | FRAGMENTSHADER'''
    p[0] = p[1]

def p_stage(p):
    'stage : stage_name EQ one_or_more_ids'
    stage = Stage()
    stage.name = p[1]
    stage.source_names = p[3]
    p[0] = stage

def p_stage_list(p):
    '''stage_list   : stage
                    | stage_list stage'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_properties(p):
    'properties : PROPERTIES LBRACE property_list RBRACE'
    props = PropertyList()
    props.items = p[3]
    p[0] = props

def p_property(p):
    '''property : ID LPAREN property_arguments RPAREN
                | ID LPAREN property_arguments RPAREN EQ constant'''
    prop = Property()
    ui_name, ui_type = p[3]
    ui_default = p[6] if len(p) == 7 else None

    # If no type info and we have a default, guess type
    if ui_type is None and ui_default is not None:
        if isinstance(ui_default, tuple):
            if len(ui_default) == 2:
                ui_type = 'vec2'
            elif len(ui_default) == 3:
                ui_type = 'vec3'
            elif len(ui_default) == 4:
                ui_type = 'vec4'
        elif isinstance(ui_default, int):
            ui_type = 'int'
        elif isinstance(ui_default, float):
            ui_type = 'float'
        
    if ui_type is None:
        raise Exception(
            'Cannot infer type for property "{}"'.format(p[1])
        )

    prop.uniform = p[1]
    prop.ui_name = ui_name
    prop.ui_type = ui_type
    prop.ui_default = ui_default

    p[0] = prop

def p_property_arguments(p):
    '''property_arguments   : STRING_CONST
                            | STRING_CONST COMMA property_type'''
    p[0] = [p[1], p[3]] if len(p) == 4 else [p[1], None]

def p_property_type(p):
    '''property_type    : INT
                        | FLOAT
                        | VEC2
                        | VEC3
                        | VEC4
                        | COLOR
                        | TEXTURE2D'''
    p[0] = p[1]

def p_property_list(p):
    '''property_list    : property
                        | property_list property'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_number(p):
    '''number   : INT_CONST
                | FLOAT_CONST'''
    p[0] = p[1]

def p_constant_vec2(p):
    'constant_vec2 : LPAREN number COMMA number RPAREN'
    p[0] = (p[2], p[4])

def p_constant_vec3(p):
    'constant_vec3 : LPAREN number COMMA number COMMA number RPAREN'
    p[0] = (p[2], p[4], p[6])

def p_constant_vec4(p):
    'constant_vec4 : LPAREN number COMMA number COMMA number COMMA number RPAREN'
    p[0] = (p[2], p[4], p[6], p[8])

def p_constant(p):
    '''constant : STRING_CONST
                | number
                | constant_vec2
                | constant_vec3
                | constant_vec4'''
    p[0] = p[1]

def p_empty(p):
    'empty :'
    pass

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
