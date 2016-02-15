import unittest
import mock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
import validations


class TestValidations(unittest.TestCase):

    def test_validates_presence_when_present(self):
        validator = validations.present
        validator.name = "age"
        self.assertTrue(validator(mock.Mock(age="me")))
        self.assertTrue(validator(mock.Mock(age=17)))
        self.assertTrue(validator(mock.Mock(age=True)))

    def test_validates_presence_when_not_present(self):
        validator = validations.present
        validator.name = "age"
        self.assertFalse(validator(mock.Mock(age="")))
        self.assertFalse(validator(mock.Mock(age=False)))
        self.assertFalse(validator(mock.Mock(age=None)))

    def test_validates_absence_when_present(self):
        validator = validations.absent
        validator.name = "age"
        self.assertFalse(validator(mock.Mock(age=17)))
        self.assertFalse(validator(mock.Mock(age=True)))

    def test_validates_absence_when_not_present(self):
        validator = validations.absent
        validator.name = "age"
        self.assertTrue(validator(mock.Mock(age="")))
        self.assertTrue(validator(mock.Mock(age=False)))
        self.assertTrue(validator(mock.Mock(age=None)))

    def test_validates_uniqueness_when_unique(self):
        validator = validations.unique
        validator.name = "age"
        record = mock.Mock(age=15, __class__=mock.Mock())
        klass = record.__class__
        klass.where.return_value.where.return_value = []
        self.assertTrue(validator(record))

    def test_validates_uniqueness_when_not_unique(self):
        validator = validations.unique
        validator.name = "age"
        record = mock.Mock(age=15, __class__=mock.Mock())
        klass = record.__class__
        klass.where.return_value.where.return_value = [mock.Mock()]
        self.assertFalse(validator(record))

    def test_validates_length_when_too_short(self):
        validator = validations.length(within=range(2, 5))
        validator.name = "age"
        self.assertFalse(validator(mock.Mock(age="")))

    def test_validates_length_when_too_long(self):
        validator = validations.length(within=range(2, 5))
        validator.name = "age"
        self.assertFalse(validator(mock.Mock(age="asfafds")))

    def test_validates_length_when_correct(self):
        validator = validations.length(within=range(2, 5))
        validator.name = "age"
        self.assertTrue(validator(mock.Mock(age="abcd")))


if __name__ == '__main__':
    unittest.main()
