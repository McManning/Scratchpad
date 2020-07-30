
import re 
from libs.ply import lex

keywords = {
    # Major blocks
    'Shader':       'SHADER',
    'Properties':   'PROPERTIES',
    'Technique':    'TECHNIQUE',
    'Pass':         'PASS',

    # Shader specifiers
    'Vertex':                   'VERTEXSHADER', 
    'TessellationControl':      'TESSCONTROLSHADER',
    'TessellationEvaluation':   'TESSEVALSHADER', 
    'Geometry':                 'GEOMETRYSHADER',
    'Fragment':                 'FRAGMENTSHADER',

    # Property type specifiers
    'int':      'INT', 
    'float':    'FLOAT',
    'vec2':     'VEC2', 
    'vec3':     'VEC3',
    'vec4':     'VEC4',
    'color':    'COLOR',
    'texture2D':'TEXTURE2D',
}

tokens = tuple(keywords.values()) + (
    'LBRACE', 'RBRACE',
    'LPAREN', 'RPAREN',
    'LBRACKET', 'RBRACKET',
    'EQ', 'LT', 'GT',

    'COMMA',
    'COLON',
    'SEMI',

    'ID', 'STRING_CONST',
    'INT_CONST', 'FLOAT_CONST',
    'BOOL_CONST',

    'COMMENT', 'CPPCOMMENT', 'GLSL'
)

states = (
    ('glsl', 'exclusive'),
)

t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_LT = r'<'
t_GT = r'>'
t_EQ = r'='
t_COMMA = r','
t_COLON = r':'
t_SEMI = r';'

# Constants
t_STRING_CONST = r'\"([^\\\n]|(\\.))*?\"'

def t_FLOAT_CONST(t):
    r'-?\d+\.\d+[fF]?'
    # r'((\d+)(\.\d+)(e(\+|-)?(\d+))? | (\d+)e(\+|-)?(\d+))([lL]|[fF])?'
    t.value = float(t.value)    
    return t

def t_INT_CONST(t):
    r'-?\d+'
    t.value = int(t.value)
    return t

def t_BOOL_CONST(t):
    r'(true|false)'
    t.value = bool(t.value == 'true')
    return t

# Spaces and tabs are ignored
t_ignore = ' \t'

# Comment (C-Style)
def t_COMMENT(t):
    r'/\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count('\n')
    # return t

# Comment (C++-Style)
def t_CPPCOMMENT(t):
    r'//.*\n'
    t.lexer.lineno += 1
    # return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_begin_glsl(t):
    r'GLSL\s+[A-Za-z_][A-Za-z0-9_]*\s*\{'
    t.lexer.glsl_begin = t.lexer.lexpos
    t.lexer.brace_level = 1
    t.lexer.begin('glsl')
    
    # TODO: Better way to extract this?
    match = re.match(
        r'GLSL\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{',
        t.value,
        re.MULTILINE
    )
    t.lexer.glsl_name = match.group(1)
    t.lexer.lineno += t.value.count('\n')

    #t.type = 'ID'
    #t.value = t.value[0]
    #return t

def t_glsl_lbrace(t):
    r'\{'
    t.lexer.brace_level += 1

def t_glsl_rbrace(t):
    r'\}'
    t.lexer.brace_level -= 1
    if t.lexer.brace_level == 0:
        code = t.lexer.lexdata[t.lexer.glsl_begin:t.lexer.lexpos-1]
        t.value = (t.lexer.glsl_name, code)
        t.type = 'GLSL'
        t.lexer.lineno += code.count('\n')
        t.lexer.begin('INITIAL')
        return t

def t_glsl_nonspace(t):
    r'[^\s]+'

t_glsl_ignore = ' \t\n'

# Identifiers
def t_ID(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    if t.value in keywords:
        t.type = keywords[t.value] 
    # elif t.value in varying_attributes:
    #     t.type = t.value
    
    t.value = t.value
    return t

# Error handling rule
def t_error(t):
    print('Illegal token `{}`'.format(t.value[0]))
    t.lexer.skip(1)

# Build the lexer
lexer = lex.lex() #debug=False)
