import unittest
import mock
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from lazy_record import Query

class TunaCasserole(object):
    __attributes__ = {"my_attr": int}

    @classmethod
    def from_dict(TunaCasserole, **kwargs):
        return "mytestvalue"

@mock.patch("lazy_record.Query.db")
class TestQuery(unittest.TestCase):
    def test_gets_table_name(self, _):
        self.assertEqual("tuna_casseroles",
            Query.table_name(TunaCasserole))

    def test_makes_query_for_all_records(self, db):
        list(Query(TunaCasserole).all())
        db.execute.assert_called_once_with(
            "select id, created_at, my_attr from tuna_casseroles", [])

    def test_where_restricts_query(self, db):
        list(Query(TunaCasserole).where(my_attr=5))
        db.execute.assert_called_once_with(
            "select id, created_at, my_attr from tuna_casseroles "
            "where tuna_casseroles.my_attr == ?", [5])

    def test_where_allows_all_after(self, db):
        list(Query(TunaCasserole).where(my_attr=5).all())
        db.execute.assert_called_once_with(
            "select id, created_at, my_attr from tuna_casseroles "
            "where tuna_casseroles.my_attr == ?", [5])

    def test_where_allows_chaining(self, db):
        list(Query(TunaCasserole).where(my_attr=5).where(id=7))
        db.execute.assert_called_once_with(
            "select id, created_at, my_attr from tuna_casseroles "
            "where tuna_casseroles.id == ? and tuna_casseroles.my_attr == ?",
            [7, 5])

    def test_gets_one_record(self, db):
        self.assertEqual("mytestvalue",
            Query(TunaCasserole).where(my_attr=5).where(id=7).first())
        db.execute.assert_called_once_with(
            "select id, created_at, my_attr from tuna_casseroles "
            "where tuna_casseroles.id == ? and tuna_casseroles.my_attr == ?",
            [7, 5])
        db.execute.return_value.fetchone.assert_called_once_with()        

if __name__ == '__main__':
    unittest.main()