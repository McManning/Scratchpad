import os 
import io
from ...lib.pcpp import Preprocessor, OutputDirective, Action

class GLSLPreprocessor(Preprocessor):
    """Preprocessor directive handling for .glsl files"""

    def on_directive_handle(self, directive, toks, ifpassthru, precedingtoks):
        """Allow PCPP to process #include directives, but nothing else"""
        if directive.value == 'include':
            return True
        
        # Strip version directives - they'll be added automatically
        if directive.value == 'version':
            raise OutputDirective(Action.IgnoreAndRemove)

        # raise OutputDirective(Action.IgnoreAndPassThrough)
        return super(GLSLPreprocessor, self).on_directive_handle(
            directive, toks, ifpassthru, precedingtoks
        )

    def parse_file(self, filename: str) -> str:
        """Parse an input file and return the processed output as a string"""
        self.add_path(os.path.dirname(os.path.abspath(filename)))
        self.includes = [filename]

        with open(filename) as f:
            data = f.read()

        # TODO: No stream wrapper here? I don't really need it 
        # but it was in the example implementations.
        output = io.StringIO()
        self.parse(data)
        self.write(output)
        result = output.getvalue()
        output.close()
        return result

    def include_to_id(self, include: str) -> int:
        """Convert an include filename to a unique ID"""
        if include in self.includes:
            return self.includes.index(include)
        
        self.includes.append(include)
        return len(self.includes) - 1

    # def get_file_ids() -> List
    #     """Retrieve all included filenames, indexed by ID"""
    #     return self.includes

    def write(self, oh):
        """Duplicate of PCPP Preprocessor.write() but instead generates
            GLSL-compat #line directives using file IDs instead of strings
        """
        lastlineno = 0
        lastsource = None
        done = False
        blanklines = 0
        while not done:
            emitlinedirective = False
            toks = []
            all_ws = True
            # Accumulate a line
            while not done:
                tok = self.token()
                if not tok:
                    done = True
                    break
                toks.append(tok)
                if tok.value[0] == '\n':
                    break
                if tok.type not in self.t_WS:
                    all_ws = False
            if not toks:
                break
            if all_ws:
                # Remove preceding whitespace so it becomes just a LF
                if len(toks) > 1:
                    tok = toks[-1]
                    toks = [ tok ]
                blanklines += toks[0].value.count('\n')
                continue
            # The line in toks is not all whitespace
            emitlinedirective = (blanklines > 6) and self.line_directive is not None
            if hasattr(toks[0], 'source'):
                if lastsource is None:
                    if toks[0].source is not None:
                        emitlinedirective = True
                    lastsource = toks[0].source
                elif lastsource != toks[0].source:
                    emitlinedirective = True
                    lastsource = toks[0].source
            # Replace consecutive whitespace in output with a single space except at any indent
            first_ws = None
            for n in range(len(toks)-1, -1, -1):
                tok = toks[n]
                if first_ws is None:
                    if tok.type in self.t_SPACE or len(tok.value) == 0:
                        first_ws = n
                else:
                    if tok.type not in self.t_SPACE and len(tok.value) > 0:
                        m = n + 1
                        while m != first_ws:
                            del toks[m]
                            first_ws -= 1
                        first_ws = None
                        if self.compress > 0:
                            # Collapse a token of many whitespace into single
                            if toks[m].value[0] == ' ':
                                toks[m].value = ' '
            if not self.compress > 1 and not emitlinedirective:
                newlinesneeded = toks[0].lineno - lastlineno - 1
                if newlinesneeded > 6 and self.line_directive is not None:
                    emitlinedirective = True
                else:
                    while newlinesneeded > 0:
                        oh.write('\n')
                        newlinesneeded -= 1
            lastlineno = toks[0].lineno
            # Account for those newlines in a multiline comment
            if toks[0].type == self.t_COMMENT1:
                lastlineno += toks[0].value.count('\n')
            if emitlinedirective and self.line_directive is not None:
                lastsource_id = 0 if lastsource is None else self.include_to_id(lastsource)
                oh.write('{} {} {}\n'.format(self.line_directive, lastlineno, lastsource_id))
            blanklines = 0
            for tok in toks:
                oh.write(tok.value)
