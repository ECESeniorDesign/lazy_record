import unittest
import mock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
from lazy_record.associations import *
import lazy_record


class Base(object):
    __dependents__ = []
    __attributes__ = {}
    def __init__(self):
        self._related_records = []


@has_many("comments")
@has_many("test_models", foreign_key="postId")
@has_many("tags", through="taggings")
class Post(Base):

    def boo(self):
        return "blah"

@has_many("things", through="test_models")
@belongs_to("post")
@has_many("test_models")
class Comment(Base):

    def foo(self):
        return "bar"

    @classmethod
    def bar(Comment):
        return "baz"

@has_one("other_thang", through="thing")
@has_one("thing")
@belongs_to("comment")
@belongs_to("post", foreign_key="postId")
class TestModel(Base):
    pass


@belongs_to("post")
@belongs_to("tag")
class Tagging(Base):
    pass


@has_many("another_things")
@has_many("posts", through="taggings")
class Tag(Base):
    pass

@has_one("other_thang", foreign_key="thingId")
@belongs_to("test_model")
class Thing(Base):
    pass

@belongs_to("thing", foreign_key="thingId")
class OtherThang(Base):
    pass

class AnotherThing(Base):
    pass

@has_many("scoped_childs",
          lambda query: query.where(year=2016),
          through="scoping_parents")
class DeepScopingParent(Base):
    pass

@has_many("scoped_childs", lambda query: query.where(name="foo"))
class ScopingParent(Base):
    pass

@belongs_to("scoping_parent")
class ScopedChild(Base):
    pass

@mock.patch("lazy_record.associations.query")
class TestBelongsTo(unittest.TestCase):
    def setUp(self):
        self.comment = Comment()
        self.comment.post_id = 1

    def test_defines_related_method(self, query):
        assert hasattr(self.comment, "post")

    def test_does_not_destroy_other_methods(self, query):
        self.assertEqual("bar", self.comment.foo())

    def test_does_not_destroy_class_methods(self, query):
        self.assertEqual("baz", Comment.bar())

    def test_makes_query_for_related_object(self, query):
        self.comment.post
        query.Query.assert_called_with(Post)
        q = query.Query.return_value
        q.where.assert_called_once_with(id=1)
        q2 = q.where.return_value
        q2.first.assert_called_once_with()

    def test_does_not_change_class_name(self, query):
        self.assertEqual(TestModel.__name__, "TestModel")

    def test_works_with_multiple_belongs_tos(self, query):
        test_model = TestModel()
        test_model.postId = 1
        test_model.comment_id = 1
        assert hasattr(test_model, "post")
        assert hasattr(test_model, "comment")

    def test_multiple_makes_correct_queries(self, query):
        test_model = TestModel()
        test_model.postId = 1
        test_model.comment_id = 17
        q = query.Query.return_value
        q2 = q.where.return_value
        # Test the first
        test_model.post
        query.Query.assert_called_with(Post)
        q.where.assert_called_with(id=1)
        q2.first.assert_called_with()
        # Test the second
        test_model.comment
        query.Query.assert_called_with(Comment)
        q.where.assert_called_with(id=17)
        q2.first.assert_called_with()

    def test_adds_foreign_key_to_attributes(self, query):
        self.assertEqual(TestModel.__attributes__["postId"], int)
        self.assertEqual(Comment.__attributes__["post_id"], int)

    def test_does_not_add_parent_as_dependents(self, query):
        self.assertNotIn("post", Comment.__dependents__)

    def test_allows_changing_of_parent_directly(self, query):
        new_post = Post()
        new_post.id = 87
        self.comment.post = new_post
        self.assertEqual(self.comment.post_id, 87)

    def test_setting_record_with_mismatch_raises(self, query):
        with self.assertRaises(lazy_record.AssociationTypeMismatch):
            not_post = Thing()
            not_post.id = 81
            self.comment.post = not_post

    def test_allows_changing_of_parent_to_None(self, query):
        self.comment.post = None
        self.assertEqual(self.comment.post_id, None)

    def test_adds_entry_to_relationships(self, query):
        self.assertIn("post", associations_for(Comment))


@mock.patch("lazy_record.associations.query")
class TestHasMany(unittest.TestCase):
    def setUp(self):
        self.post = Post()
        self.post.id = 11

    def test_defines_related_method(self, query):
        assert hasattr(self.post, "test_models")

    def test_does_not_destroy_other_methods(self, query):
        self.assertEqual("blah", self.post.boo())

    def test_does_not_destroy_class_methods(self, query):
        self.assertEqual("baz", Comment.bar())

    def test_makes_query_for_related_object(self, query):
        self.post.test_models
        query.Query.assert_called_with(TestModel, record=self.post)
        q = query.Query.return_value
        q.where.assert_called_once_with(postId=11)

    def test_does_not_change_class_name(self, query):
        self.assertEqual(TestModel.__name__, "TestModel")

    def test_works_with_multiple_has_manys(self, query):
        assert hasattr(self.post, "comments")
        assert hasattr(self.post, "test_models")

    def test_multiple_makes_correct_queries(self, query):
        q = query.Query.return_value
        # Test the first
        self.post.comments
        query.Query.assert_called_with(Comment, record=self.post)
        q.where.assert_called_with(post_id=11)
        # Test the second
        self.post.test_models
        query.Query.assert_called_with(TestModel, record=self.post)
        q.where.assert_called_with(postId=11)

    def test_adds_children_as_dependents_when_not_joined(self, query):
        self.assertIn("comments", Post.__dependents__)

    def test_adds_entry_to_relationships(self, query):
        self.assertIn("comments", associations_for(Post))
        self.assertEqual(associations_for(Post)["comments"], None)

    def test_adds_foreign_keys_for_child(self, query):
        self.assertIn("tag", foreign_keys_for(AnotherThing))
        self.assertEqual("tag_id", foreign_keys_for(AnotherThing)['tag'])

    def test_adds_associations_for_child(self, query):
        self.assertIn("tag", associations_for(AnotherThing))
        self.assertEqual(None, associations_for(AnotherThing)['tag'])
        

@mock.patch("lazy_record.associations.query")
class TestHasManyThrough(unittest.TestCase):
    def setUp(self):
        self.post = Post()
        self.post.id = 11

    def test_makes_query_for_related_objects(self, query):
        self.post.tags
        query.Query.assert_called_with(Tag, record=self.post)
        q = query.Query.return_value
        q.joins.assert_called_with("posts")
        q2 = q.joins.return_value
        q2.where.assert_called_once_with(posts=dict(id=11))

    def test_adds_joining_table_as_dependent(self, query):
        self.assertIn("taggings", Post.__dependents__)

    def test_adds_methods_for_joining_table(self, query):
        assert hasattr(self.post, "taggings")

    def test_adds_entry_to_relationships(self, query):
        self.assertIn("tags", associations_for(Post))
        self.assertEqual(associations_for(Post)["tags"], "taggings")        

    def test_adds_association_for_child(self, query):
        self.assertIn("comment", associations_for(Thing))
        self.assertEqual("test_model", associations_for(Thing)['comment'])
        

@mock.patch("lazy_record.associations.query")
class TestHasOne(unittest.TestCase):

    def setUp(self):
        self.test_model = TestModel()
        self.test_model.id = 11
        self.thing = Thing()
        self.thing.id = 17

    def test_makes_query_for_child_object(self, query):
        self.test_model.thing
        query.Query.assert_called_with(Thing, record=self.test_model)
        q = query.Query.return_value
        q.where.assert_called_with(test_model_id=11)

    def test_gets_one_record(self, query):
        q = query.Query.return_value.where.return_value
        record = q.first.return_value
        self.assertEqual(self.test_model.thing, record)
        q.first.assert_called_with()

    def test_adds_child_as_dependent(self, query):
        self.assertIn("thing", TestModel.__dependents__)

    def test_adds_child_to_relationships(self, query):
        self.assertIn("thing", associations_for(TestModel))
        self.assertEqual(associations_for(TestModel)["thing"], None)

    def test_getting_using_custom_foreign_key(self, query):
        self.thing.other_thang
        query.Query.assert_called_with(OtherThang, record=self.thing)
        q = query.Query.return_value
        q.where.assert_called_with(thingId=17)

    def test_setting_child_record(self, query):
        other_thang = OtherThang()
        other_thang2 = OtherThang()
        self.thing.other_thang = other_thang
        self.assertIn(other_thang, self.thing._related_records)
        self.assertEqual(other_thang.thingId, 17)
        query.Query.return_value.where.return_value.first.return_value = \
            other_thang
        self.thing.other_thang = other_thang2
        self.assertIn(other_thang2, self.thing._related_records)
        self.assertEqual(other_thang.thingId, None)
        self.assertEqual(other_thang2.thingId, 17)

    def test_setting_child_record_for_first_time(self, query):
        query.Query.return_value.where.return_value.first.return_value = None
        other_thang = OtherThang()
        self.thing.other_thang = other_thang
        self.assertIn(other_thang, self.thing._related_records)
        self.assertEqual(other_thang.thingId, 17)

    def test_setting_child_raises_if_types_dont_match(self, query):
        with self.assertRaises(lazy_record.AssociationTypeMismatch):
            self.thing.other_thang = Post()

    def test_adds_foreign_key(self, query):
        self.assertIn("other_thang", foreign_keys_for(Thing))
        self.assertEqual("thingId", foreign_keys_for(Thing)["other_thang"])

    def test_adds_foreign_key_to_child(self, query):
        self.assertIn("thing", foreign_keys_for(OtherThang))
        self.assertEqual("thingId", foreign_keys_for(OtherThang)["thing"])


@mock.patch("lazy_record.associations.query")
class TestHasOneThroughOne(unittest.TestCase):

    def test_joins_middle_records(self, query):
        t = TestModel()
        t.id = 93
        t.other_thang
        query.Query.assert_called_with(OtherThang, record=t)
        q = query.Query.return_value
        q.joins.assert_called_with("test_models")
        j = q.joins.return_value
        j.where.assert_called_with(test_models={"id": 93})
        w = j.where.return_value
        w.first.assert_called_with()

    def test_adds_association_to_child(self, query):
        self.assertIn("test_model", associations_for(OtherThang))
        self.assertEqual("thing", associations_for(OtherThang)["test_model"])

@mock.patch("lazy_record.associations.query")
class TestHasManyThroughOne(unittest.TestCase):

    def test_joins_middle_records(self, query):
        comment = Comment()
        comment.id = 16
        comment.things
        query.Query.assert_called_with(Thing, record=comment)
        q = query.Query.return_value
        q.joins.assert_called_with("comments")
        j = q.joins.return_value
        j.where.assert_called_with(comments={"id": 16})

class TestHasOneThroughMany(unittest.TestCase):

    def test_forbids_one_through_many(self):
        
        with self.assertRaises(lazy_record.AssociationForbidden) as e:
            @has_one("thing", through="test_models")
            @has_many("test_models")
            class Forbidden(Base):
                pass

        self.assertEqual(e.exception.message,
                         "Cannot have one 'thing' through many 'test_models'")

@mock.patch("lazy_record.associations.query")
class TestScopedAssociations(unittest.TestCase):

    def test_applies_scope(self, query):
        scoping_parent = ScopingParent()
        scoping_parent.id = 64
        scoping_parent.scoped_childs
        query.Query.assert_called_with(ScopedChild, record=scoping_parent)
        q = query.Query.return_value
        q.where.assert_called_once_with(scoping_parent_id=64)
        w = q.where.return_value
        # Test applies scope
        w.where.assert_called_with(name="foo")

    def test_applies_all_scopes_in_chain(self, query):
        dsp = DeepScopingParent()
        dsp.id = 56
        dsp.scoped_childs
        query.Query.assert_called_with(ScopedChild, record=dsp)
        q = query.Query.return_value
        q.joins.assert_called_with("deep_scoping_parents")
        j = q.joins.return_value
        j.where.assert_called_with(deep_scoping_parents={'id': 56})
        w = j.where.return_value
        # Test that the top level scope is applied
        w.where.assert_called_with(year=2016)
        s = w.where.return_value
        # Test that the through scope is applied
        s.where.assert_called_with(name="foo")

class TestFunctions(unittest.TestCase):

    def test_model_has_foreign_key_for_table_when_has_foreign_key(self):
        self.assertTrue(model_has_foreign_key_for_table("posts", Tagging))

    def test_model_has_foreign_key_for_table_when_not(self):
        self.assertFalse(model_has_foreign_key_for_table("things", TestModel))

if __name__ == '__main__':
    unittest.main()
