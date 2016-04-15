import unittest
import mock
import sys
import os
sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
from query import Query, Repo
import datetime
import query


class TunaCasserole(object):
    __all_attributes__ = {"my_attr": int, "created_at": int, "updated_at":int}
    __scopes__ = {}

    def __init__(self, **kwargs):
        self._related_records = []
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def from_dict(TunaCasserole, **kwargs):
        return kwargs

class MyRelations(object):
    pass

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
        repo.select.assert_called_with("id", "created_at",
                                       "updated_at", "my_attr")

    def test_constructs_object_with_information(self, Repo):
        repo = Repo.return_value
        fetchall_return = [(2, 33, 15)]
        fetchall = mock.Mock(return_value=fetchall_return)
        select_mock = mock.Mock(fetchall=fetchall)
        repo.select.return_value = mock.Mock(fetchall=fetchall)
        self.assertEqual(list(Query(TunaCasserole).all())[0],
            {"id": 2, "updated_at": 15, "created_at": 33})

    def test_where_restricts_query(self, Repo):
        list(Query(TunaCasserole).where(my_attr=5))
        repo = Repo.return_value
        repo.where.assert_called_with([], my_attr=5)
        repo.where.return_value.select.assert_called_with(
            "id", "created_at", "updated_at", "my_attr")

    def test_where_allows_all_after(self, Repo):
        list(Query(TunaCasserole).where(my_attr=5).all())
        repo = Repo.return_value
        repo.where.assert_called_with([], my_attr=5)
        repo.where.return_value.select.assert_called_with(
            "id", "created_at", "updated_at", "my_attr")

    def test_where_allows_chaining(self, Repo):
        list(Query(TunaCasserole).where(my_attr=5).where(id=7))
        repo = Repo.return_value
        repo.where.assert_called_with([], my_attr=5, id=7)
        repo.where.return_value.select.assert_called_with(
            "id", "created_at", "updated_at", "my_attr")

    def test_where_allows_arbitrary_queries(self, Repo):
        list(Query(TunaCasserole).where("my_attr == ?", 5))
        repo = Repo.return_value
        repo.where.assert_called_with([("my_attr == ?", 5)])
        repo.where.return_value.select.assert_called_with(
            "id", "created_at", "updated_at", "my_attr")

    def test_where_with_arbitrary_queries_allows_chaining(self, Repo):
        list(Query(TunaCasserole).where("my_attr > ?", 5).where(
            "my_attr < ?", 10))
        repo = Repo.return_value
        repo.where.assert_called_with([("my_attr > ?", 5),
                                       ("my_attr < ?", 10)])
        repo.where.return_value.select.assert_called_with(
            "id", "created_at", "updated_at", "my_attr")

    def test_allows_ordering(self, Repo):
        list(Query(TunaCasserole).order_by(id="desc").all())
        repo = Repo.return_value
        repo.order_by.assert_called_with(id="desc")
        order = repo.order_by.return_value
        order.select.assert_called_with("id", "created_at",
                                        "updated_at", "my_attr")

    def test_raises_on_multiple_orders(self, Repo):
        with self.assertRaises(query.QueryInvalid):
            q = Query(TunaCasserole).order_by(id="desc").order_by(id="asc")
            list(q.all())

    def test_gets_first_record(self, Repo):
        record = Query(TunaCasserole).where(my_attr=5).where(id=7).first()
        self.assertEqual({}, record)
        repo = Repo.return_value
        repo.where.assert_called_with([], my_attr=5, id=7)
        where = repo.where.return_value
        where.limit.assert_called_with(1)
        limit = where.limit.return_value
        limit.select.assert_called_with(
            "id", "created_at", "updated_at", "my_attr")
        select = limit.select.return_value
        select.fetchall.assert_called_once_with()

    def test_first_returns_None_if_no_first_record(self, Repo):
        repo = Repo.return_value
        where = repo.where.return_value
        where.limit.return_value.select.return_value.fetchall.return_value = []
        record = Query(TunaCasserole).where(my_attr=5).where(id=7).first()
        self.assertEqual(None, record)

    def test_first_gets_first_few_records(self, Repo):
        records = Query(TunaCasserole).where(my_attr=5).where(id=7).first(5)
        repo = Repo.return_value
        repo.where.assert_called_with([], my_attr=5, id=7)
        where = repo.where.return_value
        where.limit.assert_called_with(5)
        limit = where.limit.return_value
        limit.select.assert_called_with(
            "id", "created_at", "updated_at", "my_attr")
        select = limit.select.return_value
        select.fetchall.assert_called_once_with()

    def test_first_raises_if_count_is_zero(self, Repo):
        with self.assertRaises(query.QueryInvalid):
            Query(TunaCasserole).where(my_attr=5).where(id=7).first(0)

    def test_last_raises_if_count_is_zero(self, Repo):
        with self.assertRaises(query.QueryInvalid):
            Query(TunaCasserole).where(my_attr=5).where(id=7).last(0)

    def test_gets_last_record(self, Repo):
        record = Query(TunaCasserole).where(my_attr=5).where(id=7).last()
        self.assertEqual({}, record)
        repo = Repo.return_value
        repo.where.assert_called_with([], my_attr=5, id=7)
        where = repo.where.return_value
        where.order_by.assert_called_with(id="desc")
        order = where.order_by.return_value
        order.limit.assert_called_with(1)
        limit = order.limit.return_value
        limit.select.assert_called_with(
            "id", "created_at", "updated_at", "my_attr")
        select = limit.select.return_value
        select.fetchall.assert_called_once_with()

    def test_last_gets_last_few_records(self, Repo):
        record = Query(TunaCasserole).where(my_attr=5).where(id=7).last(5)
        repo = Repo.return_value
        repo.where.assert_called_with([], my_attr=5, id=7)
        where = repo.where.return_value
        where.order_by.assert_called_with(id="desc")
        order = where.order_by.return_value
        order.limit.assert_called_with(5)
        limit = order.limit.return_value
        limit.select.assert_called_with(
            "id", "created_at", "updated_at", "my_attr")
        select = limit.select.return_value
        select.fetchall.assert_called_once_with()

    def test_last_returns_None_if_no_last_record(self, Repo):
        repo = Repo.return_value
        where = repo.where.return_value
        order = where.order_by.return_value
        limit = order.limit.return_value
        select = limit.select.return_value
        select.fetchall.return_value = []
        record = Query(TunaCasserole).where(my_attr=5).where(id=7).last()
        self.assertEqual(None, record)

    def test_gets_last_record_with_existing_sort(self, Repo):
        r = Query(TunaCasserole).where(my_attr=5).order_by(id="desc").last()
        self.assertEqual({}, r)
        repo = Repo.return_value
        repo.where.assert_called_with([], my_attr=5)
        where = repo.where.return_value
        where.order_by.assert_called_with(id="asc")
        order = where.order_by.return_value
        order.limit.assert_called_with(1)
        limit = order.limit.return_value
        limit.select.assert_called_with(
            "id", "created_at", "updated_at", "my_attr")
        select = limit.select.return_value
        select.fetchall.assert_called_once_with()

    def test_gets_last_record_with_existing_sort_with_no_record(self, Repo):
        repo = Repo.return_value
        where = repo.where.return_value
        order = where.order_by.return_value
        limit = order.limit.return_value
        select = limit.select.return_value
        select.fetchall.return_value = []
        r = Query(TunaCasserole).where(my_attr=5).order_by(id="desc").last()
        self.assertEqual(None, r)

    def test_builds_simple_related_records(self, Repo):
        record = Query(TunaCasserole).where(my_attr=11).build()
        self.assertEqual(record.my_attr, 11)

    def test_builds_simple_related_records_with_args(self, Repo):
        record = Query(TunaCasserole).where(my_attr=11).build(my_attr=12)
        self.assertEqual(record.my_attr, 12)

    @mock.patch("query.associations.foreign_keys_for")
    def test_unrelates_records(self, fkf, Repo):
        fkf.return_value = {'tuna_casserole': 'tuna_casserole_id'}
        Repo.table_name.return_value = "tuna_casseroles"
        t = TunaCasserole()
        t2 = TunaCasserole(tuna_casserole_id=15)
        Query(TunaCasserole, record=t).delete(t2)
        self.assertEqual(t2.tuna_casserole_id, None)

    def test_displays_as_empty_query(self, Repo):
        Repo.return_value.select.return_value.fetchall.return_value = []
        self.assertEqual(repr(Query(TunaCasserole)), "<lazy_record.Query []>")

    def test_displays_as_query_with_records(self, Repo):
        Repo.return_value.select.return_value.fetchall.return_value = [
            (1, 7, datetime.datetime(2016, 1, 1))]
        # Recall that TunaCasserole overrides #from_dict to return
        # 'mytestvalue' so that is what it will repr as
        self.assertEqual(repr(Query(TunaCasserole)),
                     "<lazy_record.Query [{'created_at': 7, 'id': 1, "
                     "'updated_at': datetime.datetime(2016, 1, 1, 0, 0)}]>")

    def test_class_displays_as_though_it_was_in_lazy_record(self, Repo):
        self.assertEqual(repr(Query), "<class 'lazy_record.Query'>")

    def tests_inclusion(self, Repo):
        repo = Repo.return_value
        fetchall_return = [(15, 2, 33)]
        fetchall = mock.Mock(return_value=fetchall_return)
        select_mock = mock.Mock(fetchall=fetchall)
        repo.select.return_value = mock.Mock(fetchall=fetchall)
        self.assertIn({'created_at': 2, 'id': 15, 'updated_at': 33},
                      Query(TunaCasserole).all())

    def test_len_invokes_SQL_count_function(self, Repo):
        repo = Repo.return_value
        len(Query(TunaCasserole).all())
        repo.count.assert_called_with

    def test_returns_SQL_count(self, Repo):
        fetchone = Repo.return_value.count.return_value.fetchone
        fetchone.return_value = (2276,)
        self.assertEqual(len(Query(TunaCasserole).all()), 2276)

    def test_where_with_list_uses_sql_in(self, Repo):
        repo = Repo.return_value
        list(Query(TunaCasserole).where(name=["foo", "bar", "baz"]))
        repo.where.assert_called_with([], name=["foo", "bar", "baz"])

    def test_group_delegates_to_repo(self, Repo):
        repo = Repo.return_value
        list(Query(TunaCasserole).group("name"))
        repo.group_by.assert_called_with("name")

    def test_having_delegates_to_repo(self, Repo):
        repo = Repo.return_value
        list(Query(TunaCasserole).group("name").having("amount > ?", 15))
        repo.group_by.return_value.having.assert_called_with([("amount > ?", 15)])

    def test_select_limits_selected_attributes(self, Repo):
        repo = Repo.return_value
        list(Query(TunaCasserole).select("name"))
        repo.select.assert_called_with("name")

    def test_creates_invokes_build(self, Repo):
        query = Query(TunaCasserole).where(my_attr=11)
        query.build = mock.Mock(name="build")
        query.create(name="foo")
        query.build.assert_called_with(name="foo")

    def test_create_saves_record(self, Repo):
        record = mock.Mock(name="record")
        query = Query(TunaCasserole).where(my_attr=11)
        query.build = mock.Mock(name="build", return_value=record)
        query.create(name="foo")
        record.save.assert_called_with()

    def test_returns_saved_record(self, Repo):
        record = mock.Mock(name="record")
        query = Query(TunaCasserole).where(my_attr=11)
        query.build = mock.Mock(name="build", return_value=record)
        self.assertEqual(query.create(name="foo"), record)

    def test_find_records_when_exists(self, Repo):
        repo = Repo.return_value
        fetchone_return = {"id": 5, "my_attr": 15, "created_at": 33}
        fetchall = mock.Mock(return_value=[fetchone_return])
        repo.where.return_value.limit.return_value.select.return_value = mock.Mock(
            fetchall=fetchall)
        Query(TunaCasserole).find(5)
        repo.where.assert_called_with([], id=5)

    def test_find_raises_when_no_record(self, Repo):
        repo = Repo.return_value
        fetchall = mock.Mock(return_value=[])
        repo.where.return_value.select.return_value = mock.Mock(
            fetchall=fetchall)
        with self.assertRaises(query.RecordNotFound):
            Query(TunaCasserole).find(5)
        repo.where.assert_called_with([], id=5)

    def test_allows_finding_of_records_by_attribute(self, Repo):
        repo = Repo.return_value
        fetchone_return = {"id": 5, "my_attr": 15, "created_at": 33}
        fetchall = mock.Mock(return_value=[fetchone_return])
        repo.where.return_value.limit.return_value.select.return_value = mock.Mock(
            fetchall=fetchall)
        Query(TunaCasserole).find_by(name="foo")
        repo.where.assert_called_with([], name="foo")

    def test_raises_when_find_by_finds_nothing(self, Repo):
        repo = Repo.return_value
        fetchall = mock.Mock(return_value=[])
        repo.where.return_value.limit.return_value.select.return_value = mock.Mock(
            fetchall=fetchall)
        with self.assertRaises(query.RecordNotFound):
            Query(TunaCasserole).find_by(name="foo")
        repo.where.assert_called_with([], name="foo")


class TestRepeatedQueries(unittest.TestCase):

    def test_where_does_not_mutate_query(self):
        with mock.patch("query.Repo") as Repo:
            q = Query(TunaCasserole).where(my_attr=5)
            q.where(my_attr=3)
            list(q)
            repo = Repo.return_value
            repo.where.assert_called_with([], my_attr=5)
            repo.where.return_value.select.assert_called_with(
                "id", "created_at", "updated_at", "my_attr")

    def test_gets_last_record(self):
        q = Query(TunaCasserole).where(my_attr=5).where(id=7)
        with mock.patch("query.Repo") as Repo:
            repo = Repo.return_value
            record = q.last()
        with mock.patch("query.Repo") as Repo:
            repo = Repo.return_value
            record_2 = q.first()
            self.assertEqual({}, record_2)
            repo.where.assert_called_with([], my_attr=5, id=7)
            where = repo.where.return_value
            where.order_by.assert_not_called()
            where.limit.assert_called_with(1)
            limit = where.limit.return_value
            limit.select.assert_called_with(
                "id", "created_at", "updated_at", "my_attr")
            limit.select.return_value.fetchall.assert_called_once_with()

    def test_ordering_does_not_mutate(self):
        with mock.patch("query.Repo") as Repo:
            q = Query(TunaCasserole)
            q.order_by(id="asc")
            list(q.order_by(id="desc"))
            repo = Repo.return_value
            repo.order_by.assert_called_with(id="desc")
            order = repo.order_by.return_value
            order.select.assert_called_with("id", "created_at",
                                            "updated_at", "my_attr")


if __name__ == '__main__':
    unittest.main()
