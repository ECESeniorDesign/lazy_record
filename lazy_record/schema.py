import lazy_record.repo as repo

class Schema:
    def __init__(self, db):
        self.db = db

    def createTable(self, name):
        return CreateTable(name, self.db)

    def dropTable(self, name):
        self.db.executescript("drop table {};".format(name))

class CreateTable:
    type_mappings = {
        "string": "text",
        "integer": "integer",
        "float": "real"
    }
    def __init__(self, name, db):
        self.name = name
        self.db = db
        self.columns = []

    def __getattr__(self, attr):
        def column(name, default=None, null=True):
            column = [name, CreateTable.type_mappings[attr]]
            if default is not None:
                column.append("default {}".format(default))
            if not null:
                column.append("not null")
            self.columns.append(" ".join(column))
        if attr in CreateTable.type_mappings:
            return column
        return self.__getattribute__(attr)

    def __enter__(self):
        return self
    def __exit__(self, *args):
        lines = [
            "create table {} (".format(self.name),
            "  id integer primary key autoincrement,",
            "  " + ",\n  ".join(self.columns),
            ");"
        ]
        self.db.executescript("\n".join(lines))


def create(schema):
    with repo.Repo.db as db:
        schema(db).up()

def drop(schema):
    with repo.Repo.db as db:
        schema(db).down()