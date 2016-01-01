import re
import sqlite3

class Invalid(Exception):
    pass

class Repo(object):
    db = None

    def __init__(self, table_name):
        self.table_name = table_name
        self.where_clause = ""
        self.where_values = []
        self.inner_join_table = None
        self.order_clause = ""

    def where(self, **restrictions):
        ordered_items = self._build_where(restrictions)
        self.where_clause = "where {query} ".format(
            query = " and ".join("{table}.{attr} == ?".format(
                table = pair[0],
                attr = pair[1]
            ) for pair in ordered_items)
        )
        self.where_values = [pair[2] for pair in ordered_items]
        return self

    def _build_where(self, where_query):
        def builder(where_dict, default_table):
            for key, value in where_dict.items():
                if type(value) is dict:
                    for entry in builder(value, key):
                        yield entry
                else:
                    yield (default_table, key, value)
        return list(builder(where_query, self.table_name))

    def inner_join(self, table, on):
        self.inner_join_table = table
        self.foreign_on = on[0]
        self.local_on = on[1]
        return self

    def order_by(self, **kwargs):
        col, order = kwargs.popitem()
        self.order_clause = "order by {col} {order} ".format(
            col=col, order=order)
        return self

    @property
    def join_clause(self):
        if self.inner_join_table:
            return ("inner join {foreign_table} on "
                   "{foreign_table}.{foreign_on} == "
                   "{local_table}.{local_on} ").format(
                       foreign_table = self.inner_join_table,
                       foreign_on = self.foreign_on,
                       local_table = self.table_name,
                       local_on = self.local_on,
                   )
        else:
            return ""

    def select(self, *attributes):
        namespaced_attributes = [
            "{table}.{attr}".format(table=self.table_name, attr=attr)
            for attr in attributes
        ]
        cmd = 'select {attrs} from {table} {join_clause}{where_clause}{order_clause}'.format(
            table = self.table_name,
            attrs = ", ".join(namespaced_attributes),
            where_clause = self.where_clause,
            join_clause = self.join_clause,
            order_clause= self.order_clause,
        ).rstrip()
        return Repo.db.execute(cmd, self.where_values)

    def insert(self, **data):
        if self.where_clause:
            raise Invalid("Cannot insert with 'where' clause.")
        # Ensure that order is preserved
        data = data.items()
        cmd = "insert into {table} ({attrs}) values ({values})".format(
            table = self.table_name,
            attrs = ", ".join(entry[0] for entry in data),
            values = ", ".join(["?"] * len(data)),
        )
        handle = Repo.db.execute(cmd, [entry[1] for entry in data])
        # Return the id of the added row
        return handle.lastrowid

    def update(self, **data):
        data = data.items()
        update_command_arg = ", ".join("{} = ?".format(entry[0]) for entry in data)
        cmd = "update {table} set {update_command_arg} {where_clause}".format(
            update_command_arg=update_command_arg,
            where_clause=self.where_clause,
            table=self.table_name).rstrip()
        Repo.db.execute(cmd,
            [entry[1] for entry in data] + self.where_values)

    def delete(self):
        cmd = "delete from {table} {where_clause}".format(
            table=self.table_name,
            where_clause=self.where_clause
        ).rstrip()
        Repo.db.execute(cmd, self.where_values)

    @staticmethod
    def table_name(model):
        underscore_regex = re.compile(
            '((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
        return underscore_regex.sub(r'_\1', model.__name__).lower() + "s"

    @classmethod
    def connect_db(Repo, database=":memory:"):
        Repo.db = sqlite3.connect(database,
            detect_types=sqlite3.PARSE_DECLTYPES)
        return Repo.db
    