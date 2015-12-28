import sqlite3
import re

class Query(object):
    db = None
    echo_commands = False

    def __init__(self, model):
        self.model = model
        self.where_query = {}
        self.joiners = []
        attributes = ["id", "created_at"] + \
            list(self.model.__attributes__)
        self.attributes = [
            "{table}.{attr}".format(
                table=Query.table_name(self.model),
                attr=attr
            ) for attr in attributes
        ]

    def all(self):
        return self

    def first(self):
        record = self._do_query().fetchone()
        args = dict(zip(self.attributes, record))
        return self.model.from_dict(**args)

    def where(self, **restrictions):
        for attr, value in restrictions.items():
            self.where_query[attr] = value
        return self

    def joins(self, table):
        self.joiners.insert(0, table)
        return self

    def _build_where(self):
        def builder(where_dict, default_table):
            for key, value in where_dict.items():
                if type(value) is dict:
                    for entry in builder(value, key):
                        yield entry
                else:
                    yield (default_table, key, value)
        return list(builder(self.where_query, Query.table_name(self.model)))

    def _do_query(self):
        if self.where_query:
            ordered_items = self._build_where()
            where_clause = "where {query}".format(
                query = " and ".join("{table}.{attr} == ?".format(
                    table = pair[0],
                    attr = pair[1]
                ) for pair in ordered_items)
            )
        else:
            ordered_items = []
            where_clause = ""
        if self.joiners:
            # currently only supports 1 deep
            # looking for what multiple deep would mean
            join_clause = ("inner join {joined_table} on "
                           "{joined_table}.{our_record}_id == "
                           "{our_table}.id ").format(
                               joined_table = self.joiners[0],
                               our_record = Query.table_name(self.model)[:-1],
                               our_table = Query.table_name(self.model)
                           )
        else:
            join_clause = ""
        cmd = 'select {attrs} from {table} {join_clause}{where_clause}'.format(
            table = Query.table_name(self.model),
            attrs = ", ".join(self.attributes),
            where_clause = where_clause,
            join_clause = join_clause
        ).rstrip()
        if Query.echo_commands:
            print "SQL:", cmd, tuple(pair[2] for pair in ordered_items)
        return Query.db.execute(cmd, [pair[2] for pair in ordered_items])

    def __iter__(self):
        result = self._do_query().fetchall()
        for record in result:
            args = dict(zip(self.attributes, record))
            yield self.model.from_dict(**args)

    def __repr__(self):
        return "<{name}({model}):{records}>".format(
            name="lazy_record.Query",
            model=self.model.__name__,
            records=list(self)
        )

    @staticmethod
    def table_name(model):
        underscore_regex = re.compile(
            '((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
        return underscore_regex.sub(r'_\1', model.__name__).lower() + "s"

    @classmethod
    def connect_db(Query, database=":memory:"):
        Query.db = sqlite3.connect(database,
            detect_types=sqlite3.PARSE_DECLTYPES)

    class __metaclass__(type):
        def __repr__(self):
            return "<class 'lazy_record.Query'>"
