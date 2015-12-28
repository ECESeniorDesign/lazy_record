import sqlite3
import re

class Query(object):
    db = None

    def __init__(self, model):
        self.model = model
        self.where_query = {}
        self.attributes = ["id", "created_at"] + \
            list(self.model.__attributes__)

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

    def _do_query(self):
        if self.where_query:
            ordered_items = list(self.where_query.items())
            where_clause = "where {query}".format(
                query = " and ".join("{table}.{attr} == ?".format(
                    table = Query.table_name(self.model),
                    attr = pair[0]
                ) for pair in ordered_items)
            )
        else:
            ordered_items = []
            where_clause = ""
        cmd = 'select {attrs} from {table} {where_clause}'.format(
            table = Query.table_name(self.model),
            attrs = ", ".join(self.attributes),
            where_clause = where_clause
        ).rstrip()
        return Query.db.execute(cmd, [pair[1] for pair in ordered_items])

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
