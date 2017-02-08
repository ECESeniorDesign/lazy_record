import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from lazy_record.associations import *
import lazy_record

# INTEGRATED TEST

@has_one("other_thing", through="the_thing")
@has_one("the_thing")
@has_many("lending_tables", through="lendings")
@has_many("people", through="lendings")
@has_many("lendings")
class Book(lazy_record.Base):
    pass


@belongs_to("book")
@belongs_to("person")
@has_many("lending_tables")
class Lending(lazy_record.Base):
    pass


@has_many("the_things", through="books")
@has_many("books", through="lendings")
class Person(lazy_record.Base):
    pass

@belongs_to("lending")
class LendingTable(lazy_record.Base):
    pass

@has_one("other_thing")
@belongs_to("book")
class TheThing(lazy_record.Base):
    pass

@belongs_to("the_thing")
class OtherThing(lazy_record.Base):
    pass

@has_one("end_two", through="joiner")
@has_one("joiner")
class EndOne(lazy_record.Base):
    pass

@belongs_to("end_one")
@belongs_to("end_two")
class Joiner(lazy_record.Base):
    pass

@has_one("end_one", through="joiner")
@has_one("joiner")
class EndTwo(lazy_record.Base):
    pass

class test_schema(lazy_record.Schema):

    def up(self):
        with self.createTable("people") as t:
            pass
        with self.createTable("lendings") as t:
            t.integer("person_id", null=False)
            t.integer("book_id", null=False)
        with self.createTable("books") as t:
            pass
        with self.createTable("lending_tables") as t:
            t.integer("lending_id")
        with self.createTable("the_things") as t:
            t.integer("book_id")
        with self.createTable("other_things") as t:
            t.integer("the_thing_id")
        with self.createTable("end_ones") as t:
            pass
        with self.createTable("end_twos") as t:
            pass
        with self.createTable("joiners") as t:
            t.integer("end_one_id")
            t.integer("end_two_id")

    def down(self):
        self.dropTable("people")
        self.dropTable("lendings")
        self.dropTable("books")
        self.dropTable("lending_tables")
        self.dropTable("the_things")
        self.dropTable("other_things")
        self.dropTable("end_ones")
        self.dropTable("end_twos")
        self.dropTable("joiners")

class TestGettingRecordsThroughJoin(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.execute_schema(test_schema)
        self.person = Person.create()
        self.book = Book.create()
        self.lending = Lending.create(person_id=self.person.id,
                                      book_id=self.book.id)

    def tearDown(self):
        lazy_record.close_db()

    def test_finds_specific_records_through_many_to_many(self):
        self.assertIn(self.book.id, [b.id for b in self.person.books])

    def test_finds_records_through_many_to_many(self):
        person = Person.create()
        query = Person.joins("books")
        # Join finds the related record
        assert (self.person.id in [p.id for p in query])
        # Join does NOT find the unrelated record
        assert (person.id not in [p.id for p in query])

    def test_finds_records_through_one_to_many(self):
        person = Person.create()
        query = Person.joins("lendings")
        # Join finds the related record
        assert (self.person.id in [p.id for p in query])
        # Join does NOT find the unrelated record
        assert (person.id not in [p.id for p in query])

    def test_finds_records_through_deep_one_to_many(self):
        # import pdb; pdb.set_trace()
        lending = Lending.first()
        lending_table = LendingTable(lending_id=lending.id)
        lending_table.save()
        # import pdb; pdb.set_trace()
        self.assertIn(lending_table.id,
                      [l.id for l in self.book.lending_tables])

    def finds_records_one_deep(self):
        self.assertIn(self.lending, self.person.lendings)

class TestBuildingRecordsThroughJoin(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.execute_schema(test_schema)
        self.person = Person()
        self.person.save()

    def tearDown(self):
        lazy_record.close_db()

    def test_creates_records_and_intermediates(self):
        book = self.person.books.build()
        book.save()
        assert (book.id in [b.id for b in self.person.books])
        assert (self.person.id in [p.id for p in book.people])


class TestDestroyingRecordsThroughJoin(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.execute_schema(test_schema)
        self.person = Person()
        self.person.save()
        self.book = Book()
        self.book.save()
        Lending(person_id=self.person.id, book_id=self.book.id).save()

    def tearDown(self):
        lazy_record.close_db()

    def test_deletes_only_join_record(self):
        self.person.destroy()
        # Test that the relationship is gone
        assert len(list(self.person.books)) == 0, \
            ("Expected self.person.books to be empty, "
             "but it had count {}".format(len(list(self.person.books))))
        # test that the lending is gone
        self.assertEqual(len(list(Lending.all())), 0)
        # test that the book still exists
        assert Book.find(self.book.id).id == self.book.id

    def test_delete_on_query_unlinks_records_and_destroys_join(self):
        self.person.books.delete(self.book)
        self.person.save()
        assert len(list(self.person.books)) == 0, \
            ("Expected self.person.books to be empty, "
             "but it had count {}".format(len(list(self.person.books))))
        assert Book.find(self.book.id).id == self.book.id
        assert Person.find(self.person.id).id == self.person.id

    def test_delete_on_query_unlinks_record_on_deep_one_to_many(self):
        lending = Lending.first()
        lending_table = LendingTable(lending_id=lending.id)
        lending_table.save()
        self.book.lending_tables.delete(lending_table)
        self.book.save()
        self.assertEqual(lending_table.lending_id, None)
        # Should not destroy the lending (compare with many-to-many)
        self.assertEqual(Lending.first().id, lending.id)

    def test_raises_AssociationTypeMismatch_not_correct_type(self):
        with self.assertRaises(lazy_record.AssociationTypeMismatch) as e:
            self.person.books.delete(self.person)
        self.assertEqual(str(e.exception),
                         "Expected record of type Book, got Person.")

class TestManyThroughOne(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.execute_schema(test_schema)
        self.person = Person.create()
        self.book = Book.create()
        self.lending = Lending.create(person_id=self.person.id,
                                      book_id=self.book.id)

    def test_finds_many_through_one(self):
        thing = TheThing.create(book_id=self.book.id)
        self.assertIn(thing, self.person.the_things)

class TestOneToOne(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.execute_schema(test_schema)
        self.book = Book.create()
        self.thing = TheThing.create(book_id=self.book.id)
        self.other_thing = OtherThing.create(thing_id=self.thing.id)

    def test_sets_to_none(self):
        self.thing.other_thing = None
        self.thing.save()
        self.assertEqual(self.thing.other_thing, None)
        other_thing = OtherThing.find(self.other_thing.id)
        self.assertEqual(other_thing.the_thing_id, None)

class TestOneThroughOne(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.execute_schema(test_schema)
        self.book = Book.create()
        self.thing = TheThing.create(book_id=self.book.id)
        self.other_thing = OtherThing.create(the_thing_id=self.thing.id)

    def test_gets_record(self):
        self.assertEqual(self.book.other_thing, self.other_thing)

    def test_sets_record(self):
        another_other_thing = OtherThing()
        self.book.other_thing = another_other_thing
        self.assertEqual(another_other_thing.the_thing_id, self.thing.id)
        self.book.save()
        self.assertEqual(another_other_thing, self.book.other_thing)

    def test_disassociates_previous_record(self):
        another_other_thing = OtherThing()
        self.book.other_thing = another_other_thing
        self.book.save()
        # Need to reload the object to see the changes
        other_thing = OtherThing.find(self.other_thing.id)
        self.assertEqual(other_thing.the_thing_id, None)

    def test_sets_child_to_none(self):
        self.book.other_thing = None
        self.book.save()
        # Need to reload the object to see the changes
        other_thing = OtherThing.find(self.other_thing.id)
        self.assertEqual(other_thing.the_thing_id, None)
        self.assertEqual(self.book.other_thing, None)

    def test_gets_child_no_belongs_to(self):
        end_1 = EndOne.create()
        end_2 = EndTwo.create()
        joiner = Joiner.create(end_one_id=end_1.id, end_two_id=end_2.id)
        self.assertEqual(end_1.end_two, end_2)
        self.assertEqual(end_2.end_one, end_1)

    def test_sets_child_no_belongs_to(self):
        end_1 = EndOne.create()
        end_2 = EndTwo.create()
        end_2_new = EndTwo.create()
        joiner = Joiner.create(end_one_id=end_1.id, end_two_id=end_2.id)
        end_1.end_two = end_2_new
        end_1.save()
        self.assertEqual(end_1.end_two, end_2_new)
        self.assertEqual(end_2.end_one, None)

    def test_sets_child_to_none_no_belongs_to(self):
        end_1 = EndOne.create()
        end_2 = EndTwo.create()
        joiner = Joiner.create(end_one_id=end_1.id, end_two_id=end_2.id)
        end_1.end_two = None
        end_1.save()
        self.assertEqual(end_1.end_two, None)
        self.assertEqual(end_2.end_one, None)

class TestAddsRecords(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.execute_schema(test_schema)
        self.person = Person()
        self.person.save()
        self.book = Book()
        self.book.save()

    def tearDown(self):
        lazy_record.close_db()

    def test_appends_records_without_join(self):
        lending = Lending(person_id=self.person.id)
        self.book.lendings.append(lending)
        self.book.save()
        assert (self.book.id in [b.id for b in self.person.books])
        assert (self.person.id in [p.id for p in self.book.people])

    def test_adds_intermediaries(self):
        self.person.books.append(self.book)
        self.person.save()
        assert (self.book.id in [b.id for b in self.person.books])
        assert (self.person.id in [p.id for p in self.book.people])

    def test_raises_AssociationTypeMismatch_not_correct_type(self):
        with self.assertRaises(lazy_record.AssociationTypeMismatch) as e:
            self.person.books.append(self.person)
        self.assertEqual(str(e.exception),
                         "Expected record of type Book, got Person.")

    def test_sets_record_in_init(self):
        lending = Lending(person=self.person, book=self.book)
        lending.save()
        self.assertEqual(lending.person_id, self.person.id)
        self.assertEqual(lending.book_id, self.book.id)

if __name__ == '__main__':
    unittest.main()
