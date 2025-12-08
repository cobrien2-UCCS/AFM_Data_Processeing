import sys
import unittest

py2 = sys.version_info[0] == 2


@unittest.skipUnless(py2, "Py2/pygwy-specific tests; skipped on Py3.")
class Py2RunnerTests(unittest.TestCase):
    def test_placeholder(self):
        # These tests are intended to run in a Python 2.7 environment with pygwy installed.
        # They are skipped under Py3 in this repository. Add pygwy-specific assertions here
        # when running under the proper environment.
        self.assertTrue(py2)


if __name__ == "__main__":
    unittest.main()
