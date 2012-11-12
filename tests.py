# -*- coding: utf-8 -*-
import unittest


class ValidationToolsTest(unittest.TestCase):

    def test_is_valid_email(self):
        from app import is_valid_email

        self.assertFalse(is_valid_email(u'имейл@gmail.com'))
        self.assertFalse(is_valid_email(u'1234500'))
        self.assertFalse(is_valid_email(u'Jack'))
        self.assertFalse(is_valid_email(u'Some english'))
        self.assertFalse(is_valid_email(u'Jack@foo'))

        self.assertTrue(is_valid_email(u'Jack@foo.com'))
        self.assertTrue(is_valid_email(u'Jack.Bird@foo.com'))

    def test_is_valid_phone(self):
        from app import is_valid_phone

        self.assertFalse(is_valid_phone(u'абвгд'))
        self.assertFalse(is_valid_phone(u'+123myphone'))
        self.assertFalse(is_valid_phone(u'13444'))

        self.assertTrue(is_valid_phone(u'+13444'))

if __name__ == '__main__':
    unittest.main().runTests()
