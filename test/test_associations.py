import unittest
import mock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
from lazy_record.associations import *


class Base(object):
    __dependents__ = []
    __attributes__ = {}
    __foreign_keys__ = {}
    __associations__ = {}


@has_many("comments")
@has_many("test_models", foreign_key="postId")
@has_many("tags", through="taggings")
class Post(Base):

    def boo(self):
        return "blah"


@belongs_to("post")
@has_many("test_models")
class Comment(Base):

    def foo(self):
        return "bar"

    @classmethod
    def bar(Comment):
        return "baz"


@belongs_to("comment")
@belongs_to("post", foreign_key="postId")
class TestModel(Base):
    pass


@belongs_to("post")
@belongs_to("tag")
class Tagging(Base):
    pass


@has_many("posts", through="taggings")
class Tag(Base):
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

    def test_allows_changing_of_parent_to_None(self, query):
        self.comment.post = None
        self.assertEqual(self.comment.post_id, None)

    def test_adds_entry_to_relationships(self, query):
        self.assertIn("post", Comment.__associations__)


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
        query.Query.assert_called_with(TestModel)
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
        query.Query.assert_called_with(Comment)
        q.where.assert_called_with(post_id=11)
        # Test the second
        self.post.test_models
        query.Query.assert_called_with(TestModel)
        q.where.assert_called_with(postId=11)

    def test_adds_children_as_dependents_when_not_joined(self, query):
        self.assertIn("comments", Post.__dependents__)

    def test_adds_entry_to_relationships(self, query):
        self.assertIn("comments", Post.__associations__)
        self.assertEqual(Post.__associations__["comments"], None)


@mock.patch("lazy_record.associations.query")
class TestHasManyThrough(unittest.TestCase):
    def setUp(self):
        self.post = Post()
        self.post.id = 11

    def test_makes_query_for_related_objects(self, query):
        self.post.tags
        query.Query.assert_called_with(Tag, record=self.post)
        q = query.Query.return_value
        q.joins.assert_called_with("taggings")
        q2 = q.joins.return_value
        q2.where.assert_called_once_with(taggings=dict(post_id=11))

    def test_adds_joining_table_as_dependent(self, query):
        self.assertIn("taggings", Post.__dependents__)

    def test_adds_methods_for_joining_table(self, query):
        assert hasattr(self.post, "taggings")

    def test_adds_entry_to_relationships(self, query):
        self.assertIn("tags", Post.__associations__)
        self.assertEqual(Post.__associations__["tags"], "taggings")


if __name__ == '__main__':
    unittest.main()
