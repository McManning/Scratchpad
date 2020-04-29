
import os
import sys
import unittest

# Skip addon root to avoid mocking bpy/etc
sys.path.append(os.path.join(os.path.dirname(__file__), '../addon'))
from loader.glsl import load_shader

FIXTURES = os.path.join(os.path.dirname(__file__), './fixtures/glsl')

class TestLoader(unittest.TestCase):
    def test_adds_version_if_undeclared(self):
        shader = load_shader(FIXTURES + '/simple_no_version.glsl')
        self.assertRegex(shader, r'#version 330 core\n')

    def test_uses_existing_version(self):
        shader = load_shader(FIXTURES + '/simple.glsl')
        self.assertRegex(shader, r'\n#version 110 core\n')

    def test_injects_define_directives_with_undeclared_version(self):
        shader = load_shader(FIXTURES + '/simple_no_version.glsl', defines={
            'FOO': 'bar',
            'FIZZ': 'buzz'
        })

        self.assertRegex(shader, r'#version 330 core\n#define FOO bar\n#define FIZZ buzz\n#line \d+ ".*"\n')

    def test_injects_define_directives_after_version(self):
        shader = load_shader(FIXTURES + '/simple.glsl', defines={
            'FOO': 'bar',
            'FIZZ': 'buzz'
        })

        self.assertRegex(shader, r'\n#version 110 core\n#define FOO bar\n#define FIZZ buzz\n#line \d+ ".*"\n')

    def test_includes_relative_file(self):
        shader = load_shader(FIXTURES + '/simple_with_include.glsl')
        
        self.assertRegex(shader, r'#line 1 "func1.glsl"')
        self.assertRegex(shader, r'#line 1 "func2.glsl"')
        self.assertNotRegex(shader, r'#version 330 core', msg='#version directive not stripped from include')

        self.assertRegex(
            shader, 
            r'#line (\d+) "simple_with_include.glsl"\n// Line \1',
            msg='Generated #line N directive does not match // Line comment after includes'
        )

    def test_recursive_include_throws(self):
        with self.assertRaises(Exception):
            shader = load_shader(FIXTURES + '/recursive_include.glsl')

    def test_missing_include(self):
        with self.assertRaises(FileNotFoundError):
            shader = load_shader(FIXTURES + '/missing_include.glsl')

if __name__ == '__main__':
    unittest.main()

