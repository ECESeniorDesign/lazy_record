import unittest
import mock
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
from repo import Repo
import repo

class TunaCasserole(object):
    pass

@mock.patch("repo.Repo.db")
class TestRepo(unittest.TestCase):
    def test_gets_table_name(self, _):
        self.assertEqual("tuna_casseroles",
            Repo.table_name(TunaCasserole))
    
    @mock.patch("repo.sqlite3")
    def test_connects_database(self, sqlite3, db):
        repo.Repo.connect_db("my_db")
        sqlite3.connect.assert_called_with("my_db",
            detect_types=sqlite3.PARSE_DECLTYPES)
        self.assertEqual(repo.Repo.db, sqlite3.connect.return_value)

    def test_makes_query_for_all_records(self, db):
        Repo("tuna_casseroles").select("id", "created_at")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.id, tuna_casseroles.created_at "
            "from tuna_casseroles", [])

    def test_where_restricts_query(self, db):
        Repo("tuna_casseroles").where(my_attr=5).select("id", "created_at")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.id, tuna_casseroles.created_at "
            "from tuna_casseroles "
            "where tuna_casseroles.my_attr == ?", [5])
    def test_queries_through_tables(self, db):
        Repo("tuna_casseroles").where(
            my_relations=dict(my_attr=5)).select("id", "created_at")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.id, tuna_casseroles.created_at "
            "from tuna_casseroles "
            "where my_relations.my_attr == ?",
            [5])

    def test_joins_tables(self, db):
        Repo("tuna_casseroles").inner_join("my_relations",
            on=["tuna_casserole_id", "id"]).select("id", "created_at")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.id, tuna_casseroles.created_at "
            "from tuna_casseroles "
            "inner join my_relations on "
            "my_relations.tuna_casserole_id == tuna_casseroles.id",
            [])

    def test_joins_tables_with_where(self, db):
        Repo("tuna_casseroles").inner_join("my_relations",
            on=["tuna_casserole_id", "id"]).where(
            my_relations=dict(my_attr=5)).select("id", "created_at")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.id, tuna_casseroles.created_at "
            "from tuna_casseroles "
            "inner join my_relations on "
            "my_relations.tuna_casserole_id == tuna_casseroles.id "
            "where my_relations.my_attr == ?",
            [5])

    def test_inserts_records(self, db):
        Repo("tuna_casseroles").insert(my_attr=7)
        db.execute.assert_called_once_with(
            "insert into tuna_casseroles (my_attr) values (?)", [7])

    def test_returns_id_of_inserted_record(self, db):
        db.execute.return_value.lastrowid = 5
        self.assertEqual(Repo("tuna_casseroles").insert(my_attr=7), 5)

    @mock.patch("repo.Repo.db")
    def test_does_not_insert_records_with_where(self, db,  _):
        with self.assertRaises(repo.Invalid):
            repo.Repo("tuna_casseroles").where(x=5).insert(my_attr=7)
        self.assertEqual(db.execute.call_count, 0, "expected not to execute db command, but did.")

    def test_updates_records(self, db):
        Repo("tuna_casseroles").update(my_attr=7)
        db.execute.assert_called_once_with(
            "update tuna_casseroles set my_attr = ?", [7])

    def test_updates_with_where(self, db):
        Repo("tuna_casseroles").where(id=15).update(my_attr=7)
        db.execute.assert_called_once_with(
            "update tuna_casseroles set my_attr = ? "
            "where tuna_casseroles.id == ?", [7, 15])

    def test_deletes_records(self, db):
        Repo("tuna_casseroles").delete()
        db.execute.assert_called_once_with(
            "delete from tuna_casseroles", [])

    def test_deletes_records_with_where(self, db):
        Repo("tuna_casseroles").where(id=11).delete()
        db.execute.assert_called_once_with(
            "delete from tuna_casseroles where tuna_casseroles.id == ?", [11])

    def test_orders_records(self, db):
        Repo("tuna_casseroles").order_by(id="desc").select("id", "created_at")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.id, tuna_casseroles.created_at from "
            "tuna_casseroles order by id desc", [])

if __name__ == '__main__':
    unittest.main()

