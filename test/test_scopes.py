import unittest
import mock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
import base


class Cantaloupe(base.Base):
    __scopes__ = {
        "ripe": lambda query: query.where(ripe=1)
    }

class Watermelon(base.Base):
    pass

class TestScopes(unittest.TestCase):

    @mock.patch("base.Query")
    def test_defines_class_method_on_model(self, Query):
        Cantaloupe.ripe()
        Query.assert_called_with(Cantaloupe)
        query = Query.return_value
        query.where.assert_called_with(ripe=1)

    def test_class_method_has_reasonable_signature(self):
        self.assertEqual(Cantaloupe.ripe.__name__, "<scope>ripe")

    @mock.patch("base.Query.where")
    def test_defines_method_on_classes_queries(self, where):
        query = base.Query(Cantaloupe)
        query.ripe()
        where.assert_called_with(ripe=1)

    @mock.patch("base.Query.where")
    def test_does_not_define_method_on_other_queries(self, where):
        query = base.Query(Cantaloupe)
        query.ripe()
        query2 = base.Query(Watermelon)
        with self.assertRaises(AttributeError) as e:
            query2.ripe()
        self.assertEqual(e.exception.message,
                         "'Query' object has no attribute 'ripe'")

    def test_does_not_impede_attribute_lookup_on_class(self):
        with self.assertRaises(AttributeError) as e:
            Cantaloupe.turnip
        self.assertEqual(e.exception.message,
                         "'Cantaloupe' has no attribute 'turnip'")

if __name__ == '__main__':
    unittest.main()
