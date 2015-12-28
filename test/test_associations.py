import unittest
import mock
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from lazy_record.associations import *
class Base(object): pass

@has_many("comments")
@has_many("test_models")
class Post(Base):
    pass

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
@belongs_to("post")
class TestModel(Base):
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
        query.Query.table_name.return_value = "posts"
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
        test_model.post_id = 1
        test_model.comment_id = 17
        query.Query.table_name.side_effect = ["posts", "comments"]
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
        query.Query.table_name.return_value = "posts"
        q = query.Query.return_value
        q2 = q.where.return_value
        q2.first.return_value = "this"
        self.assertEqual("this & that", self.comment.post())

if __name__ == '__main__':
    unittest.main()