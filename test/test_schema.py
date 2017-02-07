import unittest
import mock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import lazy_record.schema as schema

class ExampleSchema(schema.Schema):
    def up(self):
        with self.createTable("foos") as t:
            t.string("foo", default=0, null=False)
            t.integer("bar") # Should default to NULL and allow NULLs
            t.float("baz", default=0.5) # allow NULLs

    def down(self):
        self.dropTable("foos")

@mock.patch("lazy_record.schema.repo")
class TestSchema(unittest.TestCase):
    def test_create_table(self, repo):
        schema.create(ExampleSchema)
        repo.Repo.db.__enter__.assert_called_with()
        db = repo.Repo.db.__enter__.return_value
        script = "\n".join([
            "create table foos (",
            "  id integer primary key autoincrement,",
            "  foo text default 0 not null,",
            "  bar integer,",
            "  baz real default 0.5",
            ");"
            ])
        db.executescript.assert_called_with(script)

    def test_drop_table(self, repo):
        schema.drop(ExampleSchema)
        repo.Repo.db.__enter__.assert_called_with()
        db = repo.Repo.db.__enter__.return_value
        script = "drop table foos;"
        db.executescript.assert_called_with(script)

if __name__ == '__main__':
    unittest.main()
