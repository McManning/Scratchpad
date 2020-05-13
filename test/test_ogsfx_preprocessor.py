
import os
import sys
import unittest

# Skip addon root to avoid mocking bpy/etc
sys.path.append(os.path.join(os.path.dirname(__file__), '../addon/parsers'))
from ogsfx.preprocessor import OGSFXPreprocessor

FIXTURES = os.path.join(os.path.dirname(__file__), './fixtures/ogsfx')

class TestOGSFXPreprocessor(unittest.TestCase):
    maxDiff = None
    
    def test_removes_undefined_blocks(self):
        p = OGSFXPreprocessor()
        p.define('DEBUG 1')

        result = p.parse_file(FIXTURES + '/preprocessors.ogsfx')
        self.assertRegex(result, r'yes')
        self.assertNotRegex(result, r'no')

    def test_includes_other_files(self):
        p = OGSFXPreprocessor()
        result = p.parse_file(FIXTURES + '/includes.ogsfx')
        
        with open(FIXTURES + '/includes.expected.ogsfx') as f:
            expected = f.read()

        self.assertEqual(expected, result)

        # Ensure the includes are all indexed in order
        self.assertEqual(3, len(p.includes))
        self.assertRegex(p.includes[0], r'includes\.ogsfx$')
        self.assertRegex(p.includes[1], r'include\.ogsfh$')
        self.assertRegex(p.includes[2], r'include\.glslv$')

if __name__ == '__main__':
    unittest.main()

