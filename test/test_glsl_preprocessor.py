
import os
import sys
import unittest

# Skip addon root to avoid mocking bpy/etc
sys.path.append(os.path.join(os.path.dirname(__file__), '../addon/parsers'))
from glsl.preprocessor import GLSLPreprocessor

FIXTURES = os.path.join(os.path.dirname(__file__), './fixtures/glsl')

class TestGLSLPreprocessor(unittest.TestCase):
    maxDiff = None
    
    def test_removes_undefined_blocks(self):
        p = GLSLPreprocessor()
        p.define('DEBUG 1')

        result = p.parse_file(FIXTURES + '/test-preprocessors.glsl')
        self.assertRegex(result, r'yes')
        self.assertNotRegex(result, r'no')

    def test_includes_other_files(self):
        p = GLSLPreprocessor()
        result = p.parse_file(FIXTURES + '/test-includes.glsl')
        
        with open(FIXTURES + '/test-includes.expected.glsl') as f:
            expected = f.read()

        self.assertEqual(expected, result)

        # Ensure the includes are all indexed in order
        self.assertEqual(3, len(p.includes))
        self.assertRegex(p.includes[0], r'test-includes\.glsl$')
        self.assertRegex(p.includes[1], r'include\.glslv$')
        self.assertRegex(p.includes[2], r'include-with-guard\.glsl$')

    def test_strips_version(self):
        p = GLSLPreprocessor()
        result = p.parse_file(FIXTURES + '/test-version.glsl')

        self.assertNotRegex(result, '#version')

if __name__ == '__main__':
    unittest.main()

