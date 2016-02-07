import unittest
import mock
import sys
import os
sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
import base
from base import Base
import lazy_record


class MyModel(Base):
    __attributes__ = {
        "name": str,
    }
    __validates__ = {
        "name": lambda record: record.name != "invalid"
    }

    def my_childs():
        pass

class MyOtherModel(Base):
    pass

@mock.patch("base.datetime")
@mock.patch("base.Repo")
@mock.patch("base.Query")
class TestBase(unittest.TestCase):

    def test_gets_number_of_records(self, Query, Repo, datetime):
        Query.return_value.all.return_value.__len__.return_value = 3
        self.assertEqual(len(MyModel), 3)
        Query.assert_called_with(MyModel)
        q = Query.return_value
        q.all.assert_called_once_with()
        all = q.all.return_value
        all.__len__.assert_called_once_with()

    def test_creates_records(self, Query, Repo, datetime):
        Repo.table_name.return_value = "my_model"
        my_record = MyModel(name="me")
        my_record.save()
        Repo.table_name.assert_called_with(MyModel)
        Repo.assert_called_with("my_model")
        repo = Repo.return_value
        today = datetime.datetime.today.return_value
        repo.insert.assert_called_with(name="me",
                                       created_at=today,
                                       updated_at=today)

    def test_updates_records(self, Query, Repo, datetime):
        Repo.table_name.return_value = "my_model"
        my_record = MyModel(name="foo")
        my_record._id = 3
        my_record._created_at = datetime.datetime.today.return_value
        my_record.save()
        Repo.table_name.assert_called_with(MyModel)
        Repo.assert_called_with("my_model")
        repo = Repo.return_value
        repo.where.assert_called_with(id=3)
        where = repo.where.return_value
        today = datetime.datetime.today.return_value
        where.update.assert_called_with(name="foo",
                                        created_at=today,
                                        updated_at=today)

    def test_does_not_create_invalid_records(self, Query, Repo, datetime):
        Repo.table_name.return_value = "my_model"
        my_record = MyModel(name="invalid")
        with self.assertRaises(base.RecordInvalid):
            my_record.save()
        self.assertEqual(Repo.return_value.insert.call_count, 0)

    def test_does_not_update_invalid_records(self, Query, Repo, datetime):
        Repo.table_name.return_value = "my_model"
        my_record = MyModel(name="invalid")
        my_record._id = 3
        my_record._created_at = datetime.datetime.today.return_value
        with self.assertRaises(base.RecordInvalid):
            my_record.save()
        self.assertEqual(Repo.return_value.update.call_count, 0)

    def test_deletes_records(self, Query, Repo, datetime):
        Repo.table_name.return_value = "my_model"
        my_record = MyModel(name="foo")
        my_record._id = 3
        my_record._created_at = datetime.datetime.today.return_value
        my_record.delete()
        Repo.table_name.assert_called_with(MyModel)
        Repo.assert_called_with("my_model")
        repo = Repo.return_value
        repo.where.assert_called_with(id=3)
        where = repo.where.return_value
        where.delete.assert_called_with()

    def test_allows_finding_of_records_by_id(self, Query, Repo, datetime):
        MyModel.find(1)
        Query.assert_called_with(MyModel)
        query = Query.return_value
        query.find.assert_called_with(1)

    def test_allows_finding_of_records_by_attribute(self, Query, Repo, dt):
        MyModel.find_by(name="foo")
        Query.assert_called_with(MyModel)
        query = Query.return_value
        query.find_by.assert_called_with(name="foo")

    def test_allows_searching_of_records_by_attribute(self, Query, Repo, dt):
        MyModel.where(name="foo")
        Query.assert_called_with(MyModel)
        query = Query.return_value
        query.where.assert_called_with(name="foo")

    def test_allows_custom_where(self, Query, Repo, dt):
        MyModel.where("name LIKE ?", "foo")
        Query.assert_called_with(MyModel)
        query = Query.return_value
        query.where.assert_called_with("name LIKE ?", "foo")

    def test_allows_fetching_of_all_records(self, Query, Repo, datetime):
        MyModel.all()
        Query.assert_called_with(MyModel)
        query = Query.return_value
        query.all.assert_called_with()

    def test_allows_fetching_through_joins(self, Query, Repo, datetime):
        MyModel.joins("my_other_models")
        Query.assert_called_with(MyModel)
        query = Query.return_value
        query.joins.assert_called_with("my_other_models")

    def test_casts_attributes_to_correct_type(self, Query, Repo, datetime):
        m = MyModel(name=1)
        self.assertEqual(m.name, "1")

    def test_creates_from_dictionary(self, Query, Repo, datetime):
        m = MyModel.from_dict(id=1, name="foo",
                              created_at=datetime.datetime.today.return_value)
        self.assertEqual(m.id, 1)
        self.assertEqual(m.name, "foo")
        self.assertEqual(m.created_at, datetime.datetime.today.return_value)

    def test_forbids_setting_of_id(self, Query, Repo, datetime):
        m = MyModel()
        with self.assertRaises(AttributeError):
            m.id = 15

    def test_forbids_setting_of_created_at(self, Query, Repo, datetime):
        m = MyModel()
        with self.assertRaises(AttributeError):
            m.created_at = datetime.datetime.today.return_value

    def test_allows_setting_of_attributes(self, Query, Repo, datetime):
        m = MyModel()
        m.name = "turnip"
        self.assertEqual(m.name, "turnip")

    def test_forbits_instantiation_with_id(self, Query, Repo, datetime):
        with self.assertRaises(AttributeError):
            MyModel(id=3)

    def test_forbits_instantiation_with_created_at(self, Query, Repo, dt):
        with self.assertRaises(AttributeError):
            MyModel(created_at=3)

    def test_gets_first_record(self, Query, Repo, datetime):
        MyModel.first()
        Query.assert_called_with(MyModel)
        query = Query.return_value
        query.first.assert_called_with()

    def test_gets_last_record(self, Query, Repo, datetime):
        MyModel.last()
        Query.assert_called_with(MyModel)
        query = Query.return_value
        query.last.assert_called_with()

    def test_mass_assigns_records(self, Query, Repo, datetime):
        m = MyModel()
        m.update(name="foo")
        self.assertEqual(m.name, "foo")

    def test_get_does_not_cast_attr_if_none(self, Query, Repo, datetime):
        m = MyModel()
        self.assertEqual(m.name, None)

    def test_set_does_not_cast_attr_if_none(self, Query, Repo, datetime):
        m = MyModel()
        m.name = None
        self.assertEqual(m.name, None)

    def test_gets_other_attributes_without_cast(self, Query, Repo, datetime):
        m = MyModel()
        self.assertEqual(m.__class__, MyModel)

    def test_raises_if_attribute_not_found(self, Query, Repo, datetime):
        m = MyModel()
        with self.assertRaises(AttributeError):
            m.turkey

    def test_repr_displays_meaningful_represenation(self, Query, Repo, dt):
        m = MyModel()
        self.assertEqual(repr(m),
                         "MyModel(id=None, name=None, created_at=None, "
                         "updated_at=None)")

    def test_evaluates_equality_based_on_id(self, Query, Repo, dt):
        m1 = MyModel()
        m1._id = 1
        m2 = MyModel()
        m2._id = 1
        m3 = MyModel()
        m3._id = 2
        self.assertEqual(m1, m2)
        self.assertNotEqual(m1, m3)

    def test_evaluates_as_inequal_if_either_id_is_None(self, Query, Repo, dt):
        m1 = MyModel()
        m1._id = 1
        m2 = MyModel()
        m2._id = None
        m3 = MyModel()
        m3._id = None
        self.assertNotEqual(m1, m2)
        self.assertNotEqual(m2, m1)
        self.assertNotEqual(m2, m3)

    def test_evaluates_as_inequal_if_models_are_different(self, Q, R, dt):
        m1 = MyModel()
        m1._id = 1
        m2 = MyOtherModel()
        m2._id = 1
        self.assertNotEqual(m1, m2)

    def test_identical_records_evaluate_as_equal(self, Query, Repo, dt):
        m1 = MyModel()
        m1._id = None
        self.assertEqual(m1, m1)

    def test_casts_to_int_as_id(self, Query, Repo, dt):
        m = MyModel()
        m._id = 11
        self.assertEqual(int(m), 11)

    def test_casts_to_0_if_no_id(self, Query, Repo, dt):
        m = MyModel()
        m._id = None
        self.assertEqual(int(m), 0)

    def test_valid_returns_true_when_valid(self, Query, Repo, datetime):
        m = MyModel(name="valid")
        self.assertTrue(m.is_valid())

    def test_valid_returns_false_when_invalid(self, Query, Repo, datetime):
        m = MyModel(name="invalid")
        self.assertFalse(m.is_valid())

    def test_accessing_attribute_not_loaded_raises(self, Query, Repo, dt):
        m = MyModel.from_dict(id=1)
        with self.assertRaises(lazy_record.MissingAttributeError):
            m.name

    def test_accessing_attribute_not_loaded_raises_no_id(self, Query, R, dt):
        m = MyModel.from_dict(name="foo")
        with self.assertRaises(lazy_record.MissingAttributeError) as e:
            m.id
        self.assertEqual(e.exception.message,
                         "'MyModel' object has no attribute 'id'")

    def test_repr_without_timestamps(self, Query, Repo, datetime):
        m = MyModel.from_dict(name="foo")
        self.assertEqual(repr(m), "MyModel(name='foo')")

    def test_create_makes_record(self, Query, Repo, datetime):
        with mock.patch.object(MyModel.__metaclass__, "__call__") as model:
            MyModel.create(name="foo")
            Query(MyModel).create.assert_called_with(name="foo")

    def test_create_returns_record(self, Query, Repo, datetime):
        record = mock.Mock(name="record")
        Query(MyModel).create.return_value = record
        self.assertEqual(MyModel.create(), record)


@mock.patch("base.Repo")
class TestBaseDestroy(unittest.TestCase):

    def setUp(self):
        self.my_model = MyModel(name="hi")
        self.my_model._id = 5

    def test_deletes_without_dependents(self, Repo):
        self.my_model.destroy()
        Repo.assert_called_once_with("my_models")
        repo = Repo.return_value
        repo.where.assert_called_once_with(id=5)
        where = repo.where.return_value
        where.delete.assert_called_once_with()

    @mock.patch.object(MyModel, "__dependents__", new=["my_childs"])
    def test_deletes_dependents(self, Repo):
        my_childs = mock.PropertyMock()
        type(self.my_model).my_childs = my_childs
        child = mock.Mock()
        my_childs.return_value.__iter__.return_value = [child]
        self.my_model.destroy()
        my_childs.assert_called_with()
        child._do_destroy.assert_called_with()
        Repo.assert_called_with("my_models")
        repo = Repo.return_value
        repo.where.assert_called_with(id=5)
        where = repo.where.return_value
        where.delete.assert_called_with()

if __name__ == '__main__':
    unittest.main()
