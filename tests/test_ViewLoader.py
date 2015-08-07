__author__ = 'hoseinyeganloo@gmail.com'

import unittest
from razorview import pyrazor


class MyTestCase(unittest.TestCase):
    # Test Layout & body
    def test_Render(self):
        ref = open('../sampleView/child.html')
        # self.assertEqual(ref.read(),pyrazor.Render(ViewLoader.Load('sampleView/child.pyhtml'),'Hello World',False))
        print(pyrazor.render_file('../sampleView/child.pyhtml'))


if __name__ == '__main__':
    unittest.main()
