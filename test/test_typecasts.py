import unittest
import mock
import sys
import os
import typecasts
import datetime


class TestTypes(unittest.TestCase):

    def test_date_casts_date_to_date(self):
        self.assertEqual(datetime.date(2016, 1, 1),
            typecasts.date(datetime.date(2016, 1, 1)))

    def test_date_casts_datetime_to_datetime(self):
        self.assertEqual(datetime.datetime(2016, 1, 1),
            typecasts.datetime(datetime.datetime(2016, 1, 1)))


if __name__ == '__main__':
    unittest.main()
