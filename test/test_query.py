import unittest
import mock
import sys
import os
sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
from query import Query, Repo

class TunaCasserole(object):
    __attributes__ = {"my_attr": int}

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def from_dict(TunaCasserole, **kwargs):
        return "mytestvalue"

@mock.patch("query.Repo")
class TestQuery(unittest.TestCase):

    def test_instantiates_repo(self, Repo):
        Repo.table_name.return_value = "tuna_casseroles"
        list(Query(TunaCasserole).all())
        Repo.table_name.assert_called_with(TunaCasserole)
        Repo.assert_called_with("tuna_casseroles")

    def test_makes_query_for_all_records(self, Repo):
        Repo.table_name.return_value = "tuna_casseroles"
        list(Query(TunaCasserole).all())
        repo = Repo.return_value
        repo.select.assert_called_with("id", "created_at", "my_attr")

    def test_constructs_object_with_information(self, Repo):
        repo = Repo.return_value
        repo.select.return_value = mock.Mock(
            fetchall=mock.Mock(
                return_value=[{"id": 2, "my_attr": 15, "created_at": 33}]))
        self.assertEqual(list(Query(TunaCasserole).all())[0], "mytestvalue")

    def test_where_restricts_query(self, Repo):
        list(Query(TunaCasserole).where(my_attr=5))
        repo = Repo.return_value
        repo.where.assert_called_with(my_attr=5)
        repo.where.return_value.select.assert_called_with(
            "id", "created_at", "my_attr")

    def test_where_allows_all_after(self, Repo):
        list(Query(TunaCasserole).where(my_attr=5).all())
        repo = Repo.return_value
        repo.where.assert_called_with(my_attr=5)
        repo.where.return_value.select.assert_called_with(
            "id", "created_at", "my_attr")

    def test_where_allows_chaining(self, Repo):
        list(Query(TunaCasserole).where(my_attr=5).where(id=7))
        repo = Repo.return_value
        repo.where.assert_called_with(my_attr=5, id=7)
        repo.where.return_value.select.assert_called_with(
            "id", "created_at", "my_attr")

    def test_gets_one_record(self, Repo):
        self.assertEqual("mytestvalue",
            Query(TunaCasserole).where(my_attr=5).where(id=7).first())
        repo = Repo.return_value
        repo.where.assert_called_with(my_attr=5, id=7)
        where = repo.where.return_value
        where.select.assert_called_with(
            "id", "created_at", "my_attr")
        where.select.return_value.fetchone.assert_called_once_with()

    def test_joins_tables(self, Repo):
        Repo.table_name.return_value = "tuna_casseroles"
        list(Query(TunaCasserole).joins("my_relations"))
        repo = Repo.return_value
        repo.inner_join.assert_called_with("my_relations",
            on=["tuna_casserole_id", "id"])
        join = repo.inner_join.return_value
        join.select.assert_called_with(
            "id", "created_at", "my_attr")

    def test_builds_simple_related_records(self, Repo):
        record = Query(TunaCasserole).where(my_attr = 11).build()
        self.assertEqual(record.my_attr, 11)

    def test_builds_simple_related_records_with_args(self, Repo):
        record = Query(TunaCasserole).where(my_attr = 11).build(my_attr=12)
        self.assertEqual(record.my_attr, 12)

if __name__ == '__main__':
    unittest.main()
