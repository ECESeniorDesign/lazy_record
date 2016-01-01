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
        book = self.person.books().build()
        book.save()
        assert (book.id in [b.id for b in self.person.books()])
        assert (self.person.id in [p.id for p in book.persons()])

    def test_adds_intermediaries(self):
        book = Book()
        book.save()
        self.person.books().append(book)
        self.person.save()
        assert (book.id in [b.id for b in self.person.books()])
        assert (self.person.id in [p.id for p in book.persons()])

# TODO deleting records through join

if __name__ == '__main__':
    unittest.main()