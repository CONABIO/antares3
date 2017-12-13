import unittest

from madmex import util


class TestUtil(unittest.TestCase):
    def test_basename(self):
        filename = '/fake/file/path/to/file.txt'
        self.assertEqual(util.basename(filename), 'file.txt')
        self.assertEqual(util.basename(filename, True), 'file.txt')
        self.assertEqual(util.basename(filename, False), 'file')
        self.assertEqual(util.basename(filename), 'file.txt')
        self.assertEqual(util.basename(filename, suffix=True), 'file.txt')
        self.assertEqual(util.basename(filename, suffix=False), 'file')
        
if __name__ == '__main__':
    unittest.main()