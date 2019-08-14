import unittest
from os.path import exists, join

from apluslms_shepherd.build.tasks.utils import bare_clone
from apluslms_shepherd.config import DevelopmentConfig

case = [DevelopmentConfig.COURSE_REPO_BASEPATH, 'git@version.aalto.fi:dingr1/shepherdwebhookstesting.git',
        'CS-A1234', 'master', 'master', '1',
        '/u/18/dingr1/unix/code/shepherd_repo_keys/git%40version.aalto.fi%3Adingr1/shepherdwebhookstesting.git/private.pem']


class TestClone(unittest.TestCase):

    def test_clone(self):
        self.assertEqual(bare_clone(*case), 0)

    def test_exist(self):
        self.assertTrue(exists(join(DevelopmentConfig.COURSE_REPO_BASEPATH, 'shepherd_test_clone', 'builds',
                                    *case[2:3], case[5])))
