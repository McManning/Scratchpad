"""
GLSL Shader loader

Features:
    - Injecting default #version, if not supplied
    - Injecting custom #define directives
    - Support for #include directive without an extension
    - Accurate #line directives

Does not support:
    - Recursive inclusions
"""

import os 
import re

# Default version directive, if none is provided
DEFAULT_GLSL_VERSION = '330 core'

def load_shader(file: str, defines: dict = {}, depth: int = 0, is_include = False) -> str:
    if depth > 100:
        raise Exception('Include exceeds max depth. Might be a recursive inclusion')

    basename = os.path.basename(file)
    dirname = os.path.dirname(file)

    with open(file) as f:
        lines = f.readlines()

    shader = '#line 1 "{}"\n'.format(basename)
    
    line_num = 1
    has_version = False
    for line in lines:
        version_directive = re.search(r"#\s*version\s+", line, re.IGNORECASE)
        include_directive = re.search(r"#\s*include\s+[\"<'](?P<filename>.*)['>\"]", line, re.IGNORECASE)

        if version_directive:
            if is_include or has_version:
                # Ignore duplicate version directives
                shader += '\n'
                line_num += 1
            elif not has_version:
                has_version = True
                shader += line 
                line_num += 1

                # Inject custom directives after version
                for k, v in defines.items():
                    shader += '#define {} {}\n'.format(k, v)

                # Don't count injected directives as lines
                shader += '#line {} "{}"\n'.format(line_num, basename)

        elif include_directive:
            include_file = os.path.join(dirname, include_directive.group('filename'))
            shader += load_shader(include_file, depth=depth + 1, is_include=True)
            line_num += 1
            
            # Ensure we go back to the correct file/line after inclusion
            shader += '\n#line {} "{}"\n'.format(line_num, basename)

        else:
            shader += line
            line_num += 1

    # If version is never set, add a default and prepend defines
    if not has_version and not is_include:
        prepend = '#version {}\n'.format(DEFAULT_GLSL_VERSION)
        for k, v in defines.items():
            prepend += '#define {} {}\n'.format(k, v)

        shader = prepend + shader

    return shader
