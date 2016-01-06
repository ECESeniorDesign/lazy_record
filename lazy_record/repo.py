import re
import sqlite3


class Invalid(Exception):
    pass


class Repo(object):
    """
    Wrapper object around the database.
    """
    db = None

    def __init__(self, table_name):
        """
        Instantiates a Repo object for the passed +table_name+ for adding,
        updating, or destroying records in that table.
        """
        self.table_name = table_name
        self.where_clause = ""
        self.where_values = []
        self.inner_joins = []
        self.order_clause = ""

    def where(self, **restrictions):
        """
        Analog to SQL "WHERE". Currently only supports ==. Does not perform
        a query until `select` is called. Returns a repo object.

        ex)

        >>> Repo("foos").where(id=11).select("*")
        SELECT foos.* FROM foos WHERE id == 11
        """
        ordered_items = self._build_where(restrictions)
        self.where_clause = "where {query} ".format(
            query=" and ".join("{table}.{attr} == ?".format(
                table=pair[0],
                attr=pair[1]
            ) for pair in ordered_items)
        )
        self.where_values = [pair[2] for pair in ordered_items]
        return self

    def _build_where(self, where_query):
        # Recursively loops through the where query to produce a list of
        # 3-tuples that contain the (table name, column, value)
        def builder(where_dict, default_table):
            for key, value in where_dict.items():
                if type(value) is dict:
                    for entry in builder(value, key):
                        yield entry
                else:
                    yield (default_table, key, value)
        return list(builder(where_query, self.table_name))

    def inner_join(self, *joiners):
        """
        Analog to SQL "INNER JOIN". +joiners+ is a list with entries of the
        form:

        {
            'table': <table_name>,
            'on': [<foreign_key>, <local_id>]
        }

        Example:

        >>> Repo('bs').inner_join(
            {'table': 'cs', on: ['b_id', 'id']}).select("*")
        SELECT bs.* FROM bs INNER JOIN cs ON cs.b_id == bs.id
        """
        def inner_joins(js, current_table):
            for joiner in js:
                yield (((current_table, joiner['on'][1]),
                        (joiner['table'], joiner['on'][0])))
                current_table = joiner['table']

        self.inner_joins = list(inner_joins(joiners, self.table_name))
        return self

    def order_by(self, **kwargs):
        """
        Analog to SQL "ORDER BY". +kwargs+ should only contain one item.

        examples)

        NO:  repo.order_by()
        NO:  repo.order_by(id="desc", name="asc")

        YES: repo.order_by(id="asc)
        """
        col, order = kwargs.popitem()
        self.order_clause = "order by {col} {order} ".format(
            col=col, order=order)
        return self

    @property
    def join_clause(self):
        # Internal use only, but the API should be stable, except for when we
        # add support for multi-level joins
        return "".join(("inner join {foreign_table} on "
                "{foreign_table}.{foreign_on} == "
                "{local_table}.{local_on} ").format(
                   foreign_table=inner_join[1][0],
                   foreign_on=inner_join[1][1],
                   local_table=inner_join[0][0],
                   local_on=inner_join[0][1],
               ) for inner_join in self.inner_joins)

    def select(self, *attributes):
        """
        Select the passed +attributes+ from the table, subject to the
        restrictions provided by the other methods in this class.

        ex)

        >>> Repo("foos").select("name", "id")
        SELECT foos.name, foos.id FROM foos
        """
        namespaced_attributes = [
            "{table}.{attr}".format(table=self.table_name, attr=attr)
            for attr in attributes
        ]
        cmd = ('select {attrs} from {table} '
               '{join_clause}{where_clause}{order_clause}').format(
            table=self.table_name,
            attrs=", ".join(namespaced_attributes),
            where_clause=self.where_clause,
            join_clause=self.join_clause,
            order_clause=self.order_clause,
        ).rstrip()
        return Repo.db.execute(cmd, self.where_values)

    def insert(self, **data):
        """
        Insert the passed +data+ into the table. Raises Invalid if a where
        clause is present (i.e. no INSERT INTO table WHERE)
        """
        if self.where_clause:
            raise Invalid("Cannot insert with 'where' clause.")
        # Ensure that order is preserved
        data = data.items()
        cmd = "insert into {table} ({attrs}) values ({values})".format(
            table=self.table_name,
            attrs=", ".join(entry[0] for entry in data),
            values=", ".join(["?"] * len(data)),
        )
        handle = Repo.db.execute(cmd, [entry[1] for entry in data])
        # Return the id of the added row
        return handle.lastrowid

    def update(self, **data):
        """
        Update records in the table with +data+. Often combined with `where`,
        as it acts on all records in the table unless restricted.

        ex)

        >>> Repo("foos").update(name="bar")
        UPDATE foos SET name = "bar"
        """
        data = data.items()
        update_command_arg = ", ".join("{} = ?".format(entry[0])
                                       for entry in data)
        cmd = "update {table} set {update_command_arg} {where_clause}".format(
            update_command_arg=update_command_arg,
            where_clause=self.where_clause,
            table=self.table_name).rstrip()
        Repo.db.execute(cmd, [entry[1] for entry in data] + self.where_values)

    def delete(self):
        """
        Remove entries from the table. Often combined with `where`, as it acts
        on all records in the table unless restricted.
        """
        cmd = "delete from {table} {where_clause}".format(
            table=self.table_name,
            where_clause=self.where_clause
        ).rstrip()
        Repo.db.execute(cmd, self.where_values)

    @staticmethod
    def table_name(model):
        """
        Get a model's table name. (e.g. MyModel => "my_models")
        """
        underscore_regex = re.compile(
            '((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
        return underscore_regex.sub(r'_\1', model.__name__).lower() + "s"

    @classmethod
    def connect_db(Repo, database=":memory:"):
        """
        Connect Repo to a database with path +database+ so all instances can
        interact with the database.
        """
        Repo.db = sqlite3.connect(database,
                                  detect_types=sqlite3.PARSE_DECLTYPES)
        return Repo.db
