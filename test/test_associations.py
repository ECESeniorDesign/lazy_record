import unittest
import mock
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
from lazy_record.associations import *
class Base(object):
    __dependents__ = []
    __attributes__ = {}
    __foreign_keys__ = {}

@has_many("comments")
@has_many("test_models", foreign_key="postId")
@has_many("tags", through="taggings")
class Post(Base):
    def comments(self):
        return super(Post, self).comments() + " & that"
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
    def post(self):
        return super(Comment, self).post() + " & that"

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

class TestBelongsTo(unittest.TestCase):
    def setUp(self):
        self.comment = Comment()
        self.comment.post_id = 1

    def test_defines_related_method(self):
        assert hasattr(self.comment, "post")

    def test_does_not_destroy_other_methods(self):
        self.assertEqual("bar", self.comment.foo())

    def test_does_not_destroy_class_methods(self):
        self.assertEqual("baz", Comment.bar())

    @mock.patch("lazy_record.associations.query")
    def test_makes_query_for_related_object(self, query):
        self.comment.post()
        query.Query.assert_called_with(Post)
        q = query.Query.return_value
        q.where.assert_called_once_with(id=1)
        q2 = q.where.return_value
        q2.first.assert_called_once_with()

    def test_does_not_change_class_name(self):
        self.assertEqual(TestModel.__name__, "TestModel")

    def test_correctly_names_parent_record_method(self):
        self.assertEqual(TestModel().post.__name__, "post")

    def test_works_with_multiple_belongs_tos(self):
        test_model = TestModel()
        assert hasattr(test_model, "post")
        assert hasattr(test_model, "comment")

    @mock.patch("lazy_record.associations.query")
    def test_multiple_makes_correct_queries(self, query):
        test_model = TestModel()
        test_model.postId = 1
        test_model.comment_id = 17
        q = query.Query.return_value
        q2 = q.where.return_value
        # Test the first
        test_model.post()
        query.Query.assert_called_with(Post)
        q.where.assert_called_with(id=1)
        q2.first.assert_called_with()
        # Test the second
        test_model.comment()
        query.Query.assert_called_with(Comment)
        q.where.assert_called_with(id=17)
        q2.first.assert_called_with()        

    @mock.patch("lazy_record.associations.query")
    def test_allows_overloading_of_parent_method(self, query):
        q = query.Query.return_value
        q2 = q.where.return_value
        q2.first.return_value = "this"
        self.assertEqual("this & that", self.comment.post())

    def test_adds_foreign_key_to_attributes(self):
        self.assertEqual(TestModel.__attributes__["postId"], int)
        self.assertEqual(Comment.__attributes__["post_id"], int)

    def test_does_not_add_parent_as_dependents(self):
        self.assertNotIn("post", Comment.__dependents__)

class TestHasMany(unittest.TestCase):
    def setUp(self):
        self.post = Post()
        self.post.id = 11

    def test_defines_related_method(self):
        assert hasattr(self.post, "test_models")

    def test_does_not_destroy_other_methods(self):
        self.assertEqual("blah", self.post.boo())

    def test_does_not_destroy_class_methods(self):
        self.assertEqual("baz", Comment.bar())

    @mock.patch("lazy_record.associations.query")
    def test_makes_query_for_related_object(self, query):
        self.post.test_models()
        query.Query.assert_called_with(TestModel)
        q = query.Query.return_value
        q.where.assert_called_once_with(postId=11)

    def test_does_not_change_class_name(self):
        self.assertEqual(TestModel.__name__, "TestModel")

    def test_correctly_names_child_record_method(self):
        self.assertEqual(self.post.test_models.__name__, "test_models")

    def test_works_with_multiple_has_manys(self):
        assert hasattr(self.post, "comments")
        assert hasattr(self.post, "test_models")

    @mock.patch("lazy_record.associations.query")
    def test_multiple_makes_correct_queries(self, query):
        q = query.Query.return_value
        # Test the first
        self.post.comments()
        query.Query.assert_called_with(Comment)
        q.where.assert_called_with(post_id=11)
        # Test the second
        self.post.test_models()
        query.Query.assert_called_with(TestModel)
        q.where.assert_called_with(postId=11)

    @mock.patch("lazy_record.associations.query")
    def test_allows_overloading_of_child_method(self, query):
        query.Query.table_name.return_value = "posts"
        q = query.Query.return_value
        q.where.return_value = "this"
        self.assertEqual("this & that", self.post.comments())

    def test_adds_children_as_dependents_when_not_joined(self):
        self.assertIn("comments", Post.__dependents__)

class TestHasManyThrough(unittest.TestCase):
    def setUp(self):
        self.post = Post()
        self.post.id = 11

    @mock.patch("lazy_record.associations.query")
    def test_makes_query_for_related_objects(self, query):
        self.post.tags()
        query.Query.assert_called_with(Tag, record=self.post)
        q = query.Query.return_value
        q.joins.assert_called_with("taggings")
        q2 = q.joins.return_value
        q2.where.assert_called_once_with(taggings=dict(post_id=11))

    def test_adds_joining_table_as_dependent(self):
        self.assertIn("taggings", Post.__dependents__)

    def test_adds_methods_for_joining_table(self):
        assert hasattr(self.post, "taggings")

if __name__ == '__main__':
    unittest.main()
