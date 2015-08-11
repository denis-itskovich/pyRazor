# Alex Lusco

import logging
import re
import types
import hashlib
import os
import os.path
from io import StringIO

import lex
import cgi


class View(object):
    """A razor view"""

    def __init__(self, razor, text, ignore_whitespace, path):
        self.razor = razor
        self.path = os.path.dirname(path)
        self.ignore_whitespace = ignore_whitespace
        self.__layout = None
        self.__layoutModel = None
        self._value = ''
        self._body = ''
        self._sections = dict()
        self.renderer = types.MethodType(self.parse(text, ignore_whitespace), self)

    def render(self, model=None):
        io = StringIO()
        self.render_to(io, model)
        self._value = io.getvalue()
        io.close()
        if self.__layout is not None:
            self._value = self.razor.render_layout(self.__layout, self._value, self.__layoutModel, self.ignore_whitespace)
        return self._value

    def render_to(self, io, model=None):
        self.model = model
        self.io = io
        self.renderer(io, model)

    # Methods below here are expected to be called from within the template
    def tmpl(self, file, submodel=None):
        chModel = submodel or self.model
        view = self.razor.render_file(file, chModel, self.ignore_whitespace)
        self.io.write(view)

    def wrap(self, path, submodel=None):
        if not os.path.isabs(path):
            path = os.path.join(self.path, path)

        self.__layoutModel = submodel or self.model
        self.__layout = path

    def section(self, name):
        # TODO(alusco): Output a section
        raise NotImplementedError("Section isn't implemented yet")

    def body(self):
        self.io.write(self._body)

    @staticmethod
    def parse(text, ignore_whitespace):
        text = re.sub("@#.*#@", "", text, flags=re.S)
        lexer = lex.RazorLexer.create(ignore_whitespace)
        builder = ViewBuilder(lexer.scope)
        for token in lexer.scan(text):
            builder.parse(token)
        return builder.build()


class ViewIO(StringIO):
    """Subclass of StringIO which can write a line"""

    def __init__(self):
        StringIO.__init__(self)
        self.scope = 0

    def set_scope(self, scope):
        self.scope = scope

    def __write_scope(self):
        self.write("  " * self.scope)

    def write(self, text):
        super(ViewIO, self).write(unicode(text))

    def write_scope(self, text):
        """Writes the text prepending the scope"""
        self.__write_scope()
        self.write(text)

    def scope_line(self, text):
        """Writes a line of text prepending the scope"""
        self.__write_scope()
        self.write_line(text)

    def write_line(self, text):
        """Writes the text followed by a \n if needed"""
        self.write(text)
        if text[-1] != '\n':
            self.write('\n')


class ViewBuilder(object):
    def __init__(self, scope):
        self.buffer = ViewIO()
        self.cache = None
        self.lasttoken = (None,)
        self.scope = scope
        self.buffer.set_scope(1)
        self._write_header()

    def _write_header(self):
        """Writes the function header"""
        # The last line here must not have a trailing \n
        self.buffer.write_line("def template(self, __io, model=None):")
        self.buffer.scope_line("view = self")

    def write_code(self, code):
        """Writes a line of code to the view buffer"""
        self.buffer.scope_line(code.lstrip(' \t'))

    def write_text(self, token):
        """Writes a token to the view buffer"""
        self.try_print_indent()
        self.buffer.write_scope("__io.write(u'")
        self.buffer.write(token)
        self.buffer.write_line("')")

    def write_expression(self, expression):
        """Writes an expression to the current line"""
        self.try_print_indent()
        self.buffer.write_scope("__e = ")
        self.buffer.write_line(expression)
        self.buffer.scope_line("if __e != None and __e != 'None':")
        self.buffer.scope += 1
        self.buffer.scope_line("__io.write(unicode(__e))")
        # We rely on a hack in maybePrintNewline to determine
        # that the last token was an expression and to output the \n at scope+1
        self.buffer.scope -= 1

    def get_template(self):
        """Retrieves the templates text"""
        if not self.cache:
            self.close()
        return self.cache

    def parse(self, token):
        if token[0] == lex.Token.CODE:
            self.write_code(token[1])
        elif token[0] == lex.Token.MULTILINE:
            self.write_code(token[1])
        elif token[0] == lex.Token.ONELINE:
            self.write_code(token[1])
        elif token[0] == lex.Token.TEXT:
            self.write_text(token[1])
        elif token[0] == lex.Token.PRINTLINE:
            self.write_text(token[1])
        elif token[0] == lex.Token.XMLFULLSTART:
            self.write_text(token[1])
        elif token[0] == lex.Token.XMLSTART:
            self.write_text(token[1])
        elif token[0] == lex.Token.XMLEND:
            self.write_text(token[1])
        elif token[0] == lex.Token.XMLSELFCLOSE:
            self.write_text(token[1])
        elif token[0] == lex.Token.PARENEXPRESSION:
            self.write_expression(token[1])
        elif token[0] == lex.Token.ESCAPED:
            self.write_text(token[1])
        elif token[0] == lex.Token.EXPRESSION:
            self.write_expression(token[1])
        elif token[0] == lex.Token.NEWLINE:
            self.try_print_newline()
            self.buffer.set_scope(self.scope.get_scope() + 1)

        self.lasttoken = token

    def try_print_indent(self):
        """Handles situationally printing indention"""
        if self.lasttoken[0] != lex.Token.NEWLINE:
            return

        if len(self.lasttoken[1]) > 0:
            self.buffer.scope_line("__io.write(u'" + self.lasttoken[1] + "')")

    def try_print_newline(self):
        """Handles situationally printing a new line"""
        if self.lasttoken is None:
            return

        # Anywhere we writecode does not need the new line character
        no_new_line = {lex.Token.CODE, lex.Token.MULTILINE, lex.Token.ONELINE}
        up_scope = {lex.Token.EXPRESSION, lex.Token.PARENEXPRESSION}
        if not self.lasttoken[0] in no_new_line:
            if self.lasttoken[0] in up_scope:
                self.buffer.scope += 1
            self.buffer.scope_line("__io.write(u'\\n')")
            if self.lasttoken[0] in up_scope:
                self.buffer.scope -= 1

    def close(self):
        if not self.cache:
            self.cache = self.buffer.getvalue()
            self.buffer.close()

    def build(self):
        # Build our code and indent it one
        code = self.get_template()
        # Compile this code
        logging.debug('Parsed code: %s', code)
        block = compile(code, "view", "exec")
        exec (block, globals(), locals())
        # Builds a method which can render a template
        return locals()['template']


class PyRazor:
    def __init__(self):
        self.__mem = dict()
        self.ViewRoot = [""]

    def __load(self, name):
        for path in self.ViewRoot:
            p = os.path.join(path, name)
            if os.path.exists(p):
                f = open(p)
                view = f.read()
                f.close()
                return view
        error = ""
        for path in self.ViewRoot:
            error += os.path.join(path, name) + " -->  Not Found!\n"
        raise EnvironmentError(error)

    def __get_view(self, name, ignore_whitespace):
        if name not in self.__mem:
            self.__mem[name] = View(self, self.__load(name), ignore_whitespace, name)
        return self.__mem[name]

    def render(self, text, model=None, ignore_whitespace=False):
        key = hashlib.md5(text.encode('utf-8')).hexdigest()
        if str(key) not in self.__mem:
            self.__mem[key] = View(self, text, ignore_whitespace, '')
        return self.__mem[key].render(model)

    def render_file(self, address, model=None, ignore_whitespace=False):
        view = self.__get_view(address, ignore_whitespace)
        return view.render(model)

    def render_layout(self, address, body, model=None, ignore_whitespace=False):
        view = self.__get_view(address, ignore_whitespace)
        view._body = body
        return view.render(model)

pyrazor = PyRazor()
