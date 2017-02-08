import lazy_record.repo as repo
from lazy_record.typecasts import datetime

tables = {}

class Schema:
    def __init__(self, db, tables, execute=True):
        self.db = db
        self.tables = tables # Dictionary
        self.execute = execute

    def create(self):
        self.up()
        script = "\n".join(table.script for table in self.tables.values())
        if self.execute:
            self.db.executescript(script)

    def createTable(self, name):
        table = Table(name)
        self.tables[name] = table
        return table

    def dropTable(self, name):
        if self.execute:
            self.db.executescript("drop table {};".format(name))
        del self.tables[name]

class Table:
    type_mappings = {
        "string": "text",
        "integer": "integer",
        "float": "real",
        "timestamp": "timestamp",
        "boolean": "integer",
    }
    def __init__(self, name):
        self.name = name
        self.columns = []
        script = None

    def __getattr__(self, attr):
        def column(name, default=None, null=True):
            self.columns.append(Column(name, attr, default, null))
        if attr in Table.type_mappings:
            return column
        return self.__getattribute__(attr)

    # For creating tables only
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.columns.extend([
            Column("created_at", "timestamp", None, False),
            Column("updated_at", "timestamp", None, False),
        ])
        lines = [
            "create table {} (".format(self.name),
            "  id integer primary key autoincrement,",
            "  " + ",\n  ".join(str(col) for col in self.columns),
            ");"
        ]
        self.script = "\n".join(lines)
        self.columns.append(
            Column("id", "integer", None, False)
        )

class Column:
    casts = {
        "string": str,
        "integer": int,
        "float": float,
        "timestamp": datetime,
        "boolean": bool,
    }
    def __init__(self, name, kind, default, null):
        self.name = name
        self.kind = kind
        self.default = default
        self.null = null

    def __eq__(self, other):
        return (self.name, self.kind, self.default, self.null) == \
        (other.name, other.kind, other.default, other.null)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "{}({!r}, {!r}, {!r}, {!r})".format(type(self).__name__,
                                                   self.name,
                                                   self.kind,
                                                   self.default,
                                                   self.null)

    def __str__(self):
        column = [self.name, Table.type_mappings[self.kind]]
        if self.default is not None:
            column.append("default {}".format(self.default))
        if not self.null:
            column.append("not null")
        return " ".join(column)

    def cast(self, value):
        return Column.casts[self.kind](value)

def columns_for(table_name):
    table = tables[table_name]
    return {col.name: col for col in table.columns}

def execute(schema):
    with repo.Repo.db as db:
        schema(db, tables).create()

def load(schema):
    schema(None, tables, execute=False).create()

def drop(schema):
    with repo.Repo.db as db:
        schema(db, tables).down()
