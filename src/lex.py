# Alex Lusco
import re

import sexylexer
from scopestack import ScopeStack


class Token:
    """Simple list of token names"""
    ESCAPED = "ESCAPED"
    COMMENT = "COMMENT"
    LINECOMMENT = "LINECOMMENT"
    ONELINE = "ONELINE"
    MULTILINE = "MULTILINE"
    EXPLICITMULTILINEEND = "EXPLICITMULTILINEEND"
    PARENEXPRESSION = "PARENEXPRESSION"
    EXPRESSION = "EXPRESSION"
    TEXT = "TEXT"
    CODE = "CODE"
    NEWLINE = "NEWLINE"
    INDENT = "INDENT"
    EMPTYLINE = "EMPTYLINE"
    XMLSTART = "XMLSTART"
    XMLFULLSTART = "XMLFULLSTART"
    XMLEND = "XMLEND"
    XMLSELFCLOSE = "XMLSELFCLOSE"
    PRINTLINE = "PRINTLINE"


def bind(handler):
    """Simple binding function"""
    return lambda scanner, token: handler(scanner, token);


class RazorLexer(object):
    """Encapsulates the razor token logic"""

    @staticmethod
    def create(ignore_whitespace=False):
        """Creates the rules bound to a new lexer instance"""
        lex = RazorLexer(ignore_whitespace)
        lex.rules = (
            (Token.NEWLINE, (r"[\r]?[\n][ \t]*", bind(lex.new_line))),
            (Token.ESCAPED, (r"@@", bind(lex.escaped))),
            (Token.LINECOMMENT, (r"@#[^\n]*?$", bind(lex.line_comment))),
            (Token.ONELINE, (r"@(?:import|from|model) .+$", bind(lex.one_line))),
            (Token.MULTILINE, (r"@\w*.*:$", bind(lex.multiline))),
            (Token.PARENEXPRESSION, (r"@!?\(", bind(lex.paren_expression))),
            (Token.EXPRESSION,
             (r"@!?(\w+(?:(?:\[.+\])|(?:\(.*\)))?(?:\.[a-zA-Z]+(?:(?:\[.+\])|(?:\(.*\)))?)*)", bind(lex.expression))),
            (Token.XMLFULLSTART, (r"[ \t]*<\w[^@\n]*?>", bind(lex.xml_start))),
            (Token.XMLSTART, (r"[ \t]*<\w[^@\n>]*", bind(lex.xml_start))),
            (Token.XMLEND, (r"[ \t]*</[^@\n]+[>]", bind(lex.xml_end))),
            (Token.XMLSELFCLOSE, (r"[^@]+/>[ \t]*", bind(lex.xml_self_close))),
            (Token.TEXT, (r"[^@\n<]+", bind(lex.text))),
        )
        lex.multilineRules = (
            (Token.EMPTYLINE, (r"[\r]?[\n][ \t]*$", bind(lex.empty_line))),
            (Token.EXPLICITMULTILINEEND, (r"[\r]?[\n][ \t]*\w*.*:@", bind(lex.multiline_end))),
            (Token.NEWLINE, (r"[\r]?[\n][ \t]*", bind(lex.new_line))),
            (Token.XMLFULLSTART, (r"[ \t]*<\w[^@\n]*?>", bind(lex.xml_start))),
            (Token.XMLSTART, (r"[ \t]*<\w[^@\n>]*", bind(lex.xml_start))),
            (Token.XMLEND, (r"[ \t]*</[^@\n]+[>]", bind(lex.xml_end))),
            (Token.XMLSELFCLOSE, (r"[^@]+/>[ \t]*", bind(lex.xml_self_close))),
            (Token.MULTILINE, (r"\w*.*:$", bind(lex.multiline))),
            (Token.PRINTLINE, (r"[ \t]*print[ \t]*[(][ \t]*['\"].*[\"'][ \t]*[)]", bind(lex.print_line))),
            (Token.CODE, (r".+", bind(lex.code))),
        )
        lex.lexer = sexylexer.Lexer(lex.rules, lex.multilineRules)
        return lex

    def __init__(self, ignore_whitespace):
        self.scope = ScopeStack(ignore_whitespace)
        self.ignore_whitespace = ignore_whitespace
        self.Mode = []
        self.NewLine = False

    def scan(self, text):
        """Tokenize an input string"""
        if self.ignore_whitespace:
            return self.lexer.scan(text.lstrip())
        return self.lexer.scan(text)

    # Token Parsers
    @staticmethod
    def should_escape(token):
        """Returns false if this token should not be html escaped"""
        return token[1] != '!'

    def xml_start(self, scanner, token):
        self.push_mode(scanner)
        scanner.Mode = sexylexer.ScannerMode.Text
        token = re.sub("[ \t]*<text>", "", token)
        if self.NewLine:
            self.NewLine = False
            return self.scope.indentstack.get_scope_indentation()[0] + token.replace("'", "\\'")
        return token.replace("'", "\\'")

    def xml_end(self, scanner, token):
        self.pop_mode(scanner)
        token = re.sub("[ \t]*</text>", "", token)
        if self.NewLine:
            self.NewLine = False
            return self.scope.indentstack.get_scope_indentation()[0] + token.replace("'", "\\'")
        return token.replace("'", "\\'")

    def xml_self_close(self, scanner, token):
        self.pop_mode(scanner)
        if self.NewLine:
            self.NewLine = False
            return self.scope.indentstack.get_scope_indentation()[0] + token.replace("'", "\\'")
        return token.replace("'", "\\'")

    def paren_expression(self, scanner, token):
        """Performs paren matching to find the end of a parenthesis expression"""
        start = scanner._position
        plevel = 1
        end = start
        for c in scanner.input[start:]:
            if plevel == 0:
                # Halt when we close our braces
                break;
            elif c == '(':
                plevel += 1
            elif c == ')':
                plevel -= 1
            elif c == '\n':
                # Halt at new line
                break
            end += 1
        # parse exception
        if plevel != 0:
            raise sexylexer.InvalidTokenError()
        scanner._position = end

        # Our token here is either @!( or @(
        if not self.should_escape(token):
            return scanner.input[start:end - 1]
        # We wrap the expression in a call to cgi.escape
        return "cgi.escape(str(" + scanner.input[start:end - 1] + "))"

    def multiline(self, scanner, token):
        """Handles multiline expressions"""
        if token == "@:":
            self.Mode.append(sexylexer.ScannerMode.Text)

            # sketchy situation here.
            scanner.Mode = sexylexer.ScannerMode.CODE

            def pop_multiline():
                self.pop_mode(scanner)

            self.scope.indentstack.mark_scope(pop_multiline)
            # We have to move past the end of line (this is a special case)
            # $ matches at the end of a line so it should be just +1
            scanner._position += 1
            return None
        else:
            # # Convert helper syntax to a real python function
            # if token.lower().startswith("@helper"):
            #     token = token.lower().replace("helper", "def", 1)
            self.scope.enter_scope()
            return token.lstrip('@')

    def multiline_end(self, scanner, token):
        scanner.Mode = sexylexer.ScannerMode.Text
        self.pop_mode(scanner)
        scanner._position += 1
        return token.rstrip(':@')

    def escaped(self, scanner, token):
        """Escapes the @ token directly"""
        return "@"

    def expression(self, scanner, token):
        if not self.should_escape(token):
            return token[2:]
        return "cgi.escape(str(" + token[1:] + "))"

    def one_line(self, scanner, token):
        lower_token = token.lower()
        if lower_token.startswith("@model"):
            return "isinstance(model, " + token[token.rindex(' '):] + ")"
        else:
            return token[1:]

    def line_comment(self, scanner, token):
        """Ignores comments by returning None"""
        # Move the parser past the newline character
        scanner._position += 1
        return None

    def text(self, scanner, token):
        """Returns text escaped with ' escaped"""
        return token.replace("'", "\\'")

    def print_line(self, scanner, token):
        self.pop_mode(scanner)
        token = re.match("([ \t]*print[ \t]*[(][ \t]*['\"])(.*)([\"'][ \t]*[)])", token).group(2)
        if self.NewLine:
            self.NewLine = False
            return self.scope.indentstack.get_scope_indentation()[0] + token
        return token

    def code(self, scanner, token):
        """Returns text escaped with ' escaped"""
        return token

    def new_line(self, scanner, token):
        """Handles indention scope"""
        self.NewLine = True
        nline = token.index('\n') + 1
        token = token[nline:]
        self.scope.handle_indentation(token)
        if self.ignore_whitespace:
            return ""
        return token[self.scope.indentstack.get_scope_indentation()[1]:]

    def empty_line(self, scanner, token):
        # Ignore empty line
        return None

    def pop_mode(self, scanner):
        if len(self.Mode) > 0:
            scanner.Mode = self.Mode.pop()

    def push_mode(self, scanner):
        if len(self.Mode) > 0 or scanner.Mode == sexylexer.ScannerMode.CODE:
            self.Mode.append(scanner.Mode)
