
import os
import sys
import unittest

# Skip addon root to avoid mocking bpy/etc
sys.path.append(os.path.join(os.path.dirname(__file__), '../addon/parsers'))
from ogsfx.parser import parser

from ogsfx.shaderdata import OGSFXShader

FIXTURES = os.path.join(os.path.dirname(__file__), './fixtures/ogsfx')

class TestOGSFXParser(unittest.TestCase):
    maxDiff = None
    
    def test_simple_case(self):
        """Simple shader - single pass, minimum stages, no annotations"""
        with open(FIXTURES + '/simple-codegen.ogsfx') as f:
            source = f.read()

        shader = parser.parse(source)
        
        with open(FIXTURES + '/simple-codegen.expected.p0.vs.glsl') as f:
            p0_vs_expected = f.read()

        with open(FIXTURES + '/simple-codegen.expected.p0.fs.glsl') as f:
            p0_fs_expected = f.read()

        self.assertIsInstance(shader, OGSFXShader)

        vs = shader.get_glsl('Main', 'VertexShader')
        fs = shader.get_glsl('Main', 'PixelShader')

        self.assertEqual(p0_vs_expected, vs['p0'])
        self.assertEqual(p0_fs_expected, fs['p0'])

    def test_multiple_passes(self):
        with open(FIXTURES + '/passes.ogsfx') as f:
            source = f.read()

        shader = parser.parse(source)

        vs = shader.get_glsl('Main', 'VertexShader')
        fs = shader.get_glsl('Main', 'PixelShader')

        self.assertTrue('p0' in vs)
        self.assertTrue('p0' in fs)

        self.assertTrue('p1' in vs)
        self.assertTrue('p1' in fs)

        # No fragment shader stage defined for p0
        # (Technically should be an error, since it's non-optional)
        self.assertEqual(None, fs['p0'])

        # Also test that multiple GLSLShader blocks were combined in a stage
        self.assertRegex(fs['p1'], r'Foo code block\s+Bar code block')

        
if __name__ == '__main__':
    unittest.main()

