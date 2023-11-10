import unittest
from ddt import ddt, data, unpack
from utils.repos import RepoHelper, Package

@ddt
class TestRepositoryHelper(unittest.TestCase):
    # format: first, second, expected_result
    @data(
        (Package("abc", "1.0", "1", "lala.com"),
         Package("abc", "1.0", "2", "lala.com"),
         Package("abc", "1.0", "2", "lala.com")),
        (Package("abc", "1.0", "1", "lala.com"),
         Package("abc", "1.0", "1", "lala.com"),
         Package("abc", "1.0", "1", "lala.com")),
        (Package("abc", "1.0", "2", "lala.com"),
         Package("abc", "1.0", "1", "lala.com"),
         Package("abc", "1.0", "2", "lala.com")),
    )
    @unpack
    def test_vercmp(self, first, second, expected_result):
        """
        Test that the version comparison of packages works as expected
        """
        self.assertEqual(RepoHelper.newest_package(first, second), expected_result)

