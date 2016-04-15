import re
import sqlite3
from itertools import chain
from inflector import Inflector, English

inflector = Inflector(English)


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
        self.group_clause = ""
        self.having_clause = ""
        self.having_values = []
        self.limit_value = []

    def where(self, custom_restrictions=[], **restrictions):
        """
        Analog to SQL "WHERE". Does not perform a query until `select` is
        called. Returns a repo object. Options selected through keyword
        arguments are assumed to use == unles the value is a list, tuple, or
        dictionary. List or tuple values translate to an SQL `IN` over those
        values, and a dictionary looks up under a different table when joined.

        ex)

        >>> Repo("foos").where(id=11).select("*")
        SELECT foos.* FROM foos WHERE foos.id == 11
        >>> Repo("foos").where([("id > ?", 12)]).select("*")
        SELECT foos.* FROM foos WHERE foos.id > 12
        >>> Repo("foos").where(id=[1,2,3]).select("*")
        SELECT foos.* FROM foos WHERE foos.id IN (1, 2, 3)
        """
        # Generate the SQL pieces and the relevant values
        standard_names, standard_values = self._standard_items(restrictions)
        custom_names, custom_values = self._custom_items(custom_restrictions)
        in_names, in_values = self._in_items(restrictions)
        query_names = standard_names + custom_names + in_names
        # Stitch them into a clause with values
        if query_names:
            self.where_values = standard_values + custom_values + in_values
            self.where_clause = "where {query} ".format(
                query=" and ".join(query_names))
        return self

    def _in_items(self, restrictions):
        """Generate argument pairs for queries like where(id=[1, 2])"""
        def build_in(table, name, value):
            return "{}.{} IN ({})".format(table, name,
                                          ", ".join(["?"] * len(value)))

        in_items = self._build_where(restrictions, for_in=True)
        names = [build_in(*restriction) for restriction in in_items]
        values = list(chain(*[item[2] for item in in_items]))
        return (names, values)

    def _custom_items(self, restrictions):
        """Generate argument pairs for queries like where("id > ?", 7)"""
        def scope_name(query, table):
            # The first entry in the query is the column
            # If the column already has a ".", that means that the table has
            # already been chosen
            for splitter in (" and ", " or "):
                split_query = re.split(splitter, query, re.IGNORECASE)
                query = splitter.join("{}.{}".format(table, entry)
                                      if "." not in entry else entry
                                      for entry in split_query)
            return query

        names = [scope_name(restriction[0], self.table_name)
                 for restriction in restrictions]
        values = list(chain(
            *[restriction[1:] for restriction in restrictions]))
        return (names, values)

    def _standard_items(self, restrictions):
        """Generate argument pairs for queries like where(id=2)"""
        standard_items = self._build_where(restrictions, for_in=False)
        names = ["{}.{} == ?".format(pair[0], pair[1])
                 for pair in standard_items]
        values = [item[2] for item in standard_items]
        return (names, values)

    def _build_where(self, where_query, for_in):
        # Recursively loops through the where query to produce a list of
        # 3-tuples that contain the (table name, column, value)
        def builder(where_dict, default_table, for_in):
            for key, value in where_dict.items():
                use_in = type(value) in (tuple, list)
                if type(value) is dict:
                    for entry in builder(value, key, for_in):
                        yield entry
                elif (use_in and for_in or not (use_in or for_in)):
                    yield (default_table, key, value)

        return list(builder(where_query, self.table_name, for_in))

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
        if kwargs:
            col, order = kwargs.popitem()
            self.order_clause = "order by {col} {order} ".format(
                col=col, order=order)
        return self

    def group_by(self, column):
        if column:
            self.group_clause = "GROUP BY {} ".format(column)
        return self

    def having(self, conditions):
        names = [condition[0] for condition in conditions]
        self.having_values = list(chain(
            *[condition[1:] for condition in conditions]))
        self.having_clause = "HAVING {query} ".format(
            query=" and ".join(names))
        return self

    def limit(self, count):
        """Limit number of returned rows."""
        if count == 0:
            raise Invalid("Cannot limit to 0 records.")
        self.limit_value = [count]
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

    @property
    def limit_clause(self):
        if self.limit_value != []:
            return "LIMIT ? "
        else:
            return ""

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
               '{join_clause}{where_clause}{order_clause}'
               '{group_clause}{having_clause}{limit_clause}').format(
            table=self.table_name,
            attrs=", ".join(namespaced_attributes),
            where_clause=self.where_clause,
            join_clause=self.join_clause,
            order_clause=self.order_clause,
            group_clause=self.group_clause,
            having_clause=self.having_clause,
            limit_clause=self.limit_clause,
        ).rstrip()
        return Repo.db.execute(cmd, self.where_values + self.having_values + \
                               self.limit_value)

    def count(self):
        """
        Count the number of records in the table, subject to the query.
        """
        cmd = ("select COUNT(*) from {table} "
               "{join_clause}{where_clause}{order_clause}").format(
                    table=self.table_name,
                    where_clause=self.where_clause,
                    join_clause=self.join_clause,
                    order_clause=self.order_clause).rstrip()
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
        return inflector.tableize(model.__name__)

    @classmethod
    def connect_db(Repo, database=":memory:"):
        """
        Connect Repo to a database with path +database+ so all instances can
        interact with the database.
        """
        Repo.db = sqlite3.connect(database,
                                  detect_types=sqlite3.PARSE_DECLTYPES)
        return Repo.db
