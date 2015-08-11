# Alex Lusco

import unittest

from scopestack import ScopeStack

STEP = "     "


class CallbackCounter:
    def __init__(self):
      self.count = 0


class ScopeStackTest(unittest.TestCase):
    def setUp(self):
        self.scope = ScopeStack()

    def testScopeStartsAtZero(self):
        self.assertEquals(0, self.scope.get_scope(), "Scope didn't start at zero")

    def testCallback(self):
        """Tests that the scope stack will callback when not in a scope"""
        counter = CallbackCounter()

        def scopeCallback(counter):
            counter.count += 1

        callback = lambda: scopeCallback(counter)

        # Push a callback onto stack
        self.scope.handle_indentation("")
        self.scope.indentstack.mark_scope(callback)

        # Calls the stack with a deeper indent
        self.scope.handle_indentation(STEP)
        self.assertEquals(0, self.scope.get_scope())
        self.assertEquals(0, counter.count)

        # Falls back to the original scope
        self.scope.handle_indentation("")
        self.assertEquals(1, counter.count)

    def testSingleScope(self):
        """Tests that a single scope is registered correctly"""
        self.scope.handle_indentation("")
        self.scope.enter_scope()
        self.scope.handle_indentation(STEP)
        self.assertEquals(1, self.scope.get_scope())

        self.scope.handle_indentation(2 * STEP)
        self.assertEquals(1, self.scope.get_scope())

        self.scope.handle_indentation(STEP)
        self.assertEquals(1, self.scope.get_scope())

        self.scope.handle_indentation("")
        self.assertEquals(0, self.scope.get_scope())

    def testMultiScope(self):
        """Tests a multiscope callback is called correctly"""
        self.scope.handle_indentation("")
        self.assertEquals(0, self.scope.get_scope())
        self.scope.enter_scope()

        self.scope.handle_indentation(STEP)
        self.assertEquals(1, self.scope.get_scope())
        self.scope.enter_scope()

        self.scope.handle_indentation(2 * STEP)
        self.assertEquals(2, self.scope.get_scope())
        self.scope.enter_scope()

        self.scope.handle_indentation(2 * STEP)
        self.assertEquals(2, self.scope.get_scope())

        self.scope.handle_indentation(STEP)
        self.assertEquals(1, self.scope.get_scope())

        self.scope.handle_indentation("")
        self.assertEquals(0, self.scope.get_scope())


if __name__ == '__main__':
    unittest.main()
