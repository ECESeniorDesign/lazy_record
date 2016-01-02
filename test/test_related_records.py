import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(os.path.dirname(__file__))),
    "lazy_record"))
from lazy_record.associations import *
import lazy_record

# INTEGRATED TEST

@has_many("persons", through="lendings")
class Book(lazy_record.Base):
    pass

@belongs_to("book")
@belongs_to("person")
class Lending(lazy_record.Base):
    pass

@has_many("books", through="lendings")
class Person(lazy_record.Base):
    pass

test_schema = """
drop table if exists persons;
create table persons (
  id integer primary key autoincrement,
  created_at date not null
);
drop table if exists lendings;
create table lendings (
  id integer primary key autoincrement,
  person_id integer not null,
  book_id integer not null,
  created_at date not null
);
drop table if exists books;
create table books (
  id integer primary key autoincrement,
  created_at date not null
);
"""

class TestBuildingRecordsThroughJoin(unittest.TestCase):
    def setUp(self):
        lazy_record.connect_db()
        lazy_record.Repo.db.executescript(test_schema)
        lazy_record.Repo.db.commit()
        self.person = Person()
        self.person.save()

    def test_creates_records_and_intermediates(self):
        book = self.person.books.build()
        book.save()
        assert (book.id in [b.id for b in self.person.books])
        assert (self.person.id in [p.id for p in book.persons])

    def test_adds_intermediaries(self):
        book = Book()
        book.save()
        self.person.books.append(book)
        self.person.save()
        assert (book.id in [b.id for b in self.person.books])
        assert (self.person.id in [p.id for p in book.persons])

class TestDestroyingRecordsThroughJoin(unittest.TestCase):
    def setUp(self):
        lazy_record.connect_db()
        lazy_record.Repo.db.executescript(test_schema)
        lazy_record.Repo.db.commit()
        self.person = Person()
        self.person.save()
        self.book = Book()
        self.book.save()
        Lending(person_id=self.person.id, book_id=self.book.id).save()

    def test_deletes_only_join_record(self):
        self.person.destroy()
        # Test that the relationship is gone
        assert len(list(self.person.books)) == 0, \
        ("Expected self.person.books to be empty, "
        "but it had count {}".format(len(list(self.person.books))))
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

if __name__ == '__main__':
    unittest.main()
