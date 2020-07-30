
import os
import sys
import unittest

from unittest.mock import MagicMock, patch
sys.modules['bgl'] = MagicMock()
sys.modules['bpy'] = MagicMock()

from shaders.scribble.parser import parser
from shaders.scribble.shader import ScribbleShader

FIXTURES = os.path.join(os.path.dirname(__file__), './fixtures/scribble')

class TestScribbleParser(unittest.TestCase):
    maxDiff = None

    def test_structure(self):
        """Test loading and parsing a file"""
        with open(FIXTURES + '/structure.glsl') as f:
            data = f.read()

        shader = parser.parse(data)
        self.assertIsInstance(shader, ScribbleShader)
        
        # Techniques
        self.assertEqual(1, len(shader.techniques))
        self.assertIn('Main', shader.techniques)
        
        # Passes 
        self.assertEqual(1, len(shader.techniques['Main'].passes))

        # Stages
        p = shader.techniques['Main'].passes[0]
        self.assertEqual(5, len(p.stages))

        self.assertEqual(['Common', 'MockVS'], p.stages[0].source_names)

# def repr_shader(result):
#     print('Shader {}'.format(result.name))
#     for t in result.techniques:
#         print('\tTechnique {}'.format(t.name))
#         for p in t.passes:
#             print('\t\tPass')
#             for stage in p.stages:
#                 print('\t\t\tStage {}: {}'.format(
#                     stage.name,
#                     stage.blocks
#                 ))

#     for t in result.sources:
#         print('\tGLSL {} @ {}'.format(t.name, t.lineno))
    
#     for p in result.properties:
#         print('\t{}({}, {}) = {}'.format(
#             p.uniform,
#             p.ui_name,
#             p.ui_type,
#             p.ui_default
#         ))


# def test_lexer(data: str):
#     lexer.input(data)

#     while True:
#         tok = lexer.token()
#         if not tok: 
#             break
#         print(tok)


# if __name__ == '__main__':
#     with open('foobar/samples/test.glsl') as f:
#         data = f.read()

#     test_parser(data)
