import unittest
import mock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
from repo import Repo
import repo


class TunaCasserole(object):
    pass


@mock.patch("repo.Repo.db")
class TestRepo(unittest.TestCase):

    def test_gets_table_name(self, _):
        table_name = Repo.table_name(TunaCasserole)
        self.assertEqual("tuna_casseroles", table_name)

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

    def test_where_allows_arbitrary_restriction(self, db):
        Repo("tuna_casseroles").where([("my_attr > ?", 15)]).select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "where tuna_casseroles.my_attr > ?", [15])

    def test_arbitrary_where_does_not_double_scope_column(self, db):
        Repo("tuna_casseroles").where([("tuna_casseroles.my_attr > ?",
                                        15)]).select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "where tuna_casseroles.my_attr > ?", [15])

    def test_arbitrary_where_combines_with_regular_where(self, db):
        Repo("tuna_casseroles").where([("my_attr > ?",
                                        15)], name="foo").select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "where tuna_casseroles.name == ? "
            "and tuna_casseroles.my_attr > ?", ["foo", 15])

    def test_arbitrary_where_can_accept_no_args(self, db):
        Repo("tuna_casseroles").where([("my_attr == 11",)]).select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "where tuna_casseroles.my_attr == 11", [])

    def test_arbitrary_where_can_accept_many_args(self, db):
        Repo("tuna_casseroles").where([("my_attr == ? or my_attr == ?", 5, 11)],
            ).select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "where tuna_casseroles.my_attr == ? "
            "or tuna_casseroles.my_attr == ?", [5, 11])

    def test_accepts_multiple_arbitrary_wheres(self, db):
        Repo("tuna_casseroles").where([("my_attr == ?", 5),
                                       ("my_attr == ?", 11)],
                                      ).select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "where tuna_casseroles.my_attr == ? "
            "and tuna_casseroles.my_attr == ?", [5, 11])

    def test_queries_through_tables(self, db):
        Repo("tuna_casseroles").where(
            my_relations=dict(my_attr=5)).select("id", "created_at")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.id, tuna_casseroles.created_at "
            "from tuna_casseroles "
            "where my_relations.my_attr == ?",
            [5])

    def test_joins_tables(self, db):
        Repo("tuna_casseroles").inner_join(
            {'table': "my_relations", 'on': ["tuna_casserole_id", "id"]}
            ).select("id", "created_at")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.id, tuna_casseroles.created_at "
            "from tuna_casseroles "
            "inner join my_relations on "
            "my_relations.tuna_casserole_id == tuna_casseroles.id",
            [])

    def test_joins_multiple_tables(self, db):
        # Repo("tuna_casseroles").inner_join("my_relations",
        #     on=["tuna_casserole_id", "id"]).inner_join("my_others",
        #     on=["id", "my_other_id"]).select("id", "created_at")
        Repo("tuna_casseroles").inner_join(
            {'table': "my_relations", 'on': ["tuna_casserole_id", "id"]},
            {'table': "my_others", 'on': ["id", "my_other_id"]}
            ).select("id", "created_at")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.id, tuna_casseroles.created_at "
            "from tuna_casseroles "
            "inner join my_relations on "
            "my_relations.tuna_casserole_id == tuna_casseroles.id "
            "inner join my_others on "
            "my_others.id == my_relations.my_other_id",
            [])

    def test_joins_tables_with_where(self, db):
        Repo("tuna_casseroles").inner_join(
            {'table': "my_relations", 'on': ["tuna_casserole_id", "id"]}
            ).where(my_relations=dict(my_attr=5)
            ).select("id", "created_at")
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
        self.assertEqual(db.execute.call_count, 0,
            "expected not to execute db command, but did.")

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

    def test_gets_count_of_records(self, db):
        Repo("tuna_casseroles").count()
        db.execute.assert_called_once_with(
            "select COUNT(*) from tuna_casseroles", [])

    def test_gets_count_of_records_with_other_query_elements(self, db):
        Repo("tuna_casseroles").where(id=11).count()
        db.execute.assert_called_once_with(
            "select COUNT(*) from tuna_casseroles "
            "where tuna_casseroles.id == ?", [11])

    def test_where_with_list_generates_in(self, db):
        Repo("tuna_casseroles").where(name=["foo", "bar", "baz"]).select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "where tuna_casseroles.name IN (?, ?, ?)",
            ["foo", "bar", "baz"])

    def test_where_with_list_generates_in_with_multiple(self, db):
        Repo("tuna_casseroles").where(name=["foo", "bar", "baz"],
                                      id=(1,2)).select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "where tuna_casseroles.name IN (?, ?, ?) "
            "and tuna_casseroles.id IN (?, ?)",
            ["foo", "bar", "baz", 1, 2])

    def test_group_generates_group_by_clause(self, db):
        Repo("tuna_casseroles").group_by("name").select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "GROUP BY name", [])

    def test_having_generates_having_clause(self, db):
        Repo("tuna_casseroles").group_by("name"
                              ).having([("sum(value) > ?", 11)]).select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "GROUP BY name "
            "HAVING sum(value) > ?", [11])

    def test_where_and_having_puts_values_in_correct_order(self, db):
        Repo("tuna_casseroles").where(id=87
                              ).group_by("name"
                              ).having([("sum(value) > ?", 11)]).select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "where tuna_casseroles.id == ? "
            "GROUP BY name "
            "HAVING sum(value) > ?", [87, 11])

    def test_limit_limits_number_of_returned_objects(self, db):
        Repo("tuna_casseroles").where(id=87
                              ).limit(10).select("*")
        db.execute.assert_called_once_with(
            "select tuna_casseroles.* from tuna_casseroles "
            "where tuna_casseroles.id == ? "
            "LIMIT ?", [87, 10]
        )

    def test_limit_errors_if_limit_is_zero(self, db):
        with self.assertRaises(repo.Invalid):
            Repo("tuna_casseroles").where(id=87
                                  ).limit(0).select("*")

if __name__ == '__main__':
    unittest.main()
