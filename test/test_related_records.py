import unittest
import sys
import os
# This way, we pick the lazy_record local even if one is installed
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
from lazy_record.associations import *
import lazy_record

# INTEGRATED TEST

@has_many("lending_tables", through="lendings")
@has_many("persons", through="lendings")
@has_many("lendings")
class Book(lazy_record.Base):
    pass


@belongs_to("book")
@belongs_to("person")
@has_many("lending_tables")
class Lending(lazy_record.Base):
    pass


@has_many("books", through="lendings")
@has_many("lendings")
class Person(lazy_record.Base):
    pass

@belongs_to("lending")
class LendingTable(lazy_record.Base):
    pass

test_schema = """
drop table if exists persons;
create table persons (
  id integer primary key autoincrement,
  created_at timestamp not null,
  updated_at timestamp not null
);
drop table if exists lendings;
create table lendings (
  id integer primary key autoincrement,
  person_id integer not null,
  book_id integer not null,
  created_at timestamp not null,
  updated_at timestamp not null
);
drop table if exists books;
create table books (
  id integer primary key autoincrement,
  created_at timestamp not null,
  updated_at timestamp not null
);
drop table if exists lending_tables;
create table lending_tables (
  id integer primary key autoincrement,
  lending_id integer,
  created_at timestamp not null,
  updated_at timestamp not null
);
"""


class TestGettingRecordsThroughJoin(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.load_schema(test_schema)
        self.person = Person()
        self.person.save()
        self.book = Book()
        self.book.save()
        Lending(person_id=self.person.id, book_id=self.book.id).save()

    def tearDown(self):
        lazy_record.close_db()

    def test_finds_specific_records_through_many_to_many(self):
        self.assertIn(self.book.id, [b.id for b in self.person.books])

    def test_finds_records_through_many_to_many(self):
        person = Person()
        person.save()
        query = Person.joins("books")
        # Join finds the related record
        assert (self.person.id in [p.id for p in query])
        # Join does NOT find the unrelated record
        assert (person.id not in [p.id for p in query])

    def test_finds_records_through_one_to_many(self):
        person = Person()
        person.save()
        query = Person.joins("lendings")
        # Join finds the related record
        assert (self.person.id in [p.id for p in query])
        # Join does NOT find the unrelated record
        assert (person.id not in [p.id for p in query])

    def test_finds_records_through_deep_one_to_many(self):
        lending = Lending.first()
        lending_table = LendingTable(lending_id=lending.id)
        lending_table.save()
        self.assertIn(lending_table.id,
                      [l.id for l in self.book.lending_tables])


class TestBuildingRecordsThroughJoin(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.load_schema(test_schema)
        self.person = Person()
        self.person.save()

    def tearDown(self):
        lazy_record.close_db()

    def test_creates_records_and_intermediates(self):
        book = self.person.books.build()
        book.save()
        assert (book.id in [b.id for b in self.person.books])
        assert (self.person.id in [p.id for p in book.persons])


class TestDestroyingRecordsThroughJoin(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.load_schema(test_schema)
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
        self.assertEqual(e.exception.message,
                         "Expected record of type Book, got Person.")


class TestAddsRecords(unittest.TestCase):

    def setUp(self):
        lazy_record.connect_db()
        lazy_record.load_schema(test_schema)
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
        assert (self.person.id in [p.id for p in self.book.persons])

    def test_adds_intermediaries(self):
        self.person.books.append(self.book)
        self.person.save()
        assert (self.book.id in [b.id for b in self.person.books])
        assert (self.person.id in [p.id for p in self.book.persons])

    def test_raises_AssociationTypeMismatch_not_correct_type(self):
        with self.assertRaises(lazy_record.AssociationTypeMismatch) as e:
            self.person.books.append(self.person)
        self.assertEqual(e.exception.message,
                         "Expected record of type Book, got Person.")

    def test_sets_record_in_init(self):
        lending = Lending(person=self.person, book=self.book)
        lending.save()
        self.assertEqual(lending.person_id, self.person.id)
        self.assertEqual(lending.book_id, self.book.id)

if __name__ == '__main__':
    unittest.main()
