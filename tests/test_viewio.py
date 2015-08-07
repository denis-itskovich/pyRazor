# Alex Lusco

import unittest
from razorview import ViewIO

class ScopeStackTest(unittest.TestCase):

  def setUp(self):
    self.io = ViewIO()

  def teardown(self):
    self.io.close()

  def testWriteLine(self):
    self.io.write_line("test")
    self.io.write_line("test")
    self.assertEquals("test\ntest\n", self.io.getvalue())

  def testWriteScope(self):
    self.io.set_scope(0)
    self.io.write_scope("test")

    self.io.set_scope(1)
    self.io.write_scope("test")

    self.io.set_scope(2)
    self.io.write_scope("test")
    self.assertEquals("test  test    test", self.io.getvalue())

  def testSetScope(self):
    self.io.set_scope(0)
    self.io.scope_line("test")
    self.assertEquals("test\n", self.io.getvalue())

    self.io.set_scope(1)
    self.io.scope_line("test")
    self.io.set_scope(2)
    self.io.scope_line("test")
    self.assertEquals("test\n  test\n    test\n", self.io.getvalue())

if __name__ == '__main__':
      unittest.main()
