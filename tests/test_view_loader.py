__author__ = 'hoseinyeganloo@gmail.com'

import unittest
from razorview import pyrazor


class MyTestCase(unittest.TestCase):
    # Test Layout & body
    def testRender(self):
        print(pyrazor.render_file('../sample/child.pyhtml'))

if __name__ == '__main__':
    unittest.main()
