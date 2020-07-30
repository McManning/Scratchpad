
import os
import sys
import unittest

from unittest.mock import MagicMock, patch
sys.modules['bgl'] = MagicMock()
sys.modules['bpy'] = MagicMock()

from shaders.glsl.preprocessor import GLSLPreprocessor

FIXTURES = os.path.join(os.path.dirname(__file__), './fixtures/glsl')

class TestGLSLPreprocessor(unittest.TestCase):
    maxDiff = None
    
    def test_removes_undefined_blocks(self):
        p = GLSLPreprocessor()
        p.define('DEBUG 1')

        result = p.parse_file(FIXTURES + '/preprocessors.glsl')
        self.assertRegex(result, r'yes')
        self.assertNotRegex(result, r'no')

    def test_includes_other_files(self):
        p = GLSLPreprocessor()
        result = p.parse_file(FIXTURES + '/includes.glsl')
        
        with open(FIXTURES + '/includes.expected.glsl') as f:
            expected = f.read()

        self.assertEqual(expected, result)

        # Ensure the includes are all indexed in order
        self.assertEqual(3, len(p.includes))
        self.assertRegex(p.includes[0], r'includes\.glsl$')
        self.assertRegex(p.includes[1], r'include\.glslv$')
        self.assertRegex(p.includes[2], r'include-with-guard\.glsl$')

    def test_strips_version(self):
        p = GLSLPreprocessor()
        result = p.parse_file(FIXTURES + '/version.glsl')

        self.assertNotRegex(result, '#version')

if __name__ == '__main__':
    unittest.main()

