import unittest
import mock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import lazy_record.schema as schema
from lazy_record.typecasts import datetime

class ExampleSchema(schema.Schema):
    def up(self):
        with self.createTable("foos") as t:
            t.string("foo", default=0, null=False)
            t.integer("bar") # Should default to NULL and allow NULLs
            t.float("baz", default=0.5) # allow NULLs
            t.timestamp("bux")

    def down(self):
        self.dropTable("foos")

@mock.patch("lazy_record.schema.repo")
class TestSchema(unittest.TestCase):
    def test_create_table(self, repo):
        schema.load(ExampleSchema)
        repo.Repo.db.__enter__.assert_called_with()
        db = repo.Repo.db.__enter__.return_value
        script = "\n".join([
            "create table foos (",
            "  id integer primary key autoincrement,",
            "  foo text default 0 not null,",
            "  bar integer,",
            "  baz real default 0.5,",
            "  bux timestamp,",
            "  created_at timestamp not null,",
            "  updated_at timestamp not null",
            ");"
            ])
        db.executescript.assert_called_with(script)

    def test_drop_table(self, repo):
        schema.drop(ExampleSchema)
        repo.Repo.db.__enter__.assert_called_with()
        db = repo.Repo.db.__enter__.return_value
        script = "drop table foos;"
        db.executescript.assert_called_with(script)

    def test_get_columns_from_table(self, repo):
        schema.load(ExampleSchema)
        self.assertEqual(schema.columns_for("foos"),
        {
            "id":  schema.Column("id", kind="integer", default=None, null=False),
            "foo": schema.Column("foo", kind="string", default=0, null=False),
            "bar": schema.Column("bar", kind="integer", default=None, null=True),
            "baz": schema.Column("baz", kind="float", default=0.5, null=True),
            "bux": schema.Column("bux", kind="timestamp", default=None, null=True),
            "created_at": schema.Column("created_at", kind="timestamp", default=None, null=False),
            "updated_at": schema.Column("updated_at", kind="timestamp", default=None, null=False),
        })

    def test_cast_column_value(self, repo):
        schema.load(ExampleSchema)
        value = schema.columns_for("foos")["bar"].cast("5")
        self.assertEqual(5, value)

if __name__ == '__main__':
    unittest.main()
