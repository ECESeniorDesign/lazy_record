import unittest
import mock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import lazy_record.base as base


class Cantaloupe(base.Base):
    __scopes__ = {
        "ripe": lambda query: query.where(ripe=1)
    }

class Watermelon(base.Base):
    pass

class TestScopes(unittest.TestCase):

    @mock.patch("lazy_record.base.Query")
    def test_defines_class_method_on_model(self, Query):
        Cantaloupe.ripe()
        Query.assert_called_with(Cantaloupe)
        query = Query.return_value
        query.where.assert_called_with(ripe=1)

    def test_class_method_has_reasonable_signature(self):
        self.assertEqual(Cantaloupe.ripe.__name__, "<scope>ripe")

    @mock.patch("lazy_record.base.Query.where")
    def test_defines_method_on_classes_queries(self, where):
        query = base.Query(Cantaloupe)
        query.ripe()
        where.assert_called_with(ripe=1)

    @mock.patch("lazy_record.base.Query.where")
    def test_does_not_define_method_on_other_queries(self, where):
        query = base.Query(Cantaloupe)
        query.ripe()
        query2 = base.Query(Watermelon)
        with self.assertRaises(AttributeError) as e:
            query2.ripe()
        self.assertEqual(str(e.exception),
                         "'Query' object has no attribute 'ripe'")

    def test_does_not_impede_attribute_lookup_on_class(self):
        with self.assertRaises(AttributeError) as e:
            Cantaloupe.turnip
        self.assertEqual(str(e.exception),
                         "'Cantaloupe' has no attribute 'turnip'")

if __name__ == '__main__':
    unittest.main()
