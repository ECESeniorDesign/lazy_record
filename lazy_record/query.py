from repo import Repo
import sys
import os
import types
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from inflector import Inflector, English

inflector = Inflector(English)

def does_not_mutate(func):
    """Prevents methods from mutating the receiver"""
    def wrapper(self, *args, **kwargs):
        new = self.copy()
        return func(new, *args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

class Query(object):
    """
    Generic Query object used for searching a database for records, and
    constructing records using the returned values from the database.
    """

    def __init__(self, model, record=None):
        """
        Instantiates a new Query. +model+ is the lazy_record model (i.e. class)
        that the query will be made about: the query's member objects will be
        members of +model+'s class. When +record+ is passed, it is used for
        managing related records (to ensure that associated records are upated
        on +record+'s save and visa-versa).
        """
        self.model = model
        self.record = record
        self.where_query = {}
        self.custom_where = []
        self.having_args = []
        self.join_args = []
        self._order_with = {}
        self.group_column = None
        self.limit_count = None
        self.attributes = ["id"] + list(self.model.__all_attributes__)
        self.table = Repo.table_name(self.model)

    def copy(self):
        q = Query(self.model, self.record)
        q.where_query = dict(self.where_query)
        q.custom_where = list(self.custom_where)
        q.having_args = list(self.having_args)
        q.join_args = list(self.join_args)
        q._order_with = dict(self._order_with)
        q.group_column = self.group_column
        q.attributes = list(self.attributes)
        return q

    def all(self):
        """
        Returns all records that match the query.
        """
        return self

    def find(self, id):
        """
        Find record by +id+, raising RecordNotFound if no record exists.
        """
        return self.find_by(id=id)

    def find_by(self, **kwargs):
        """
        Find first record subject to restrictions in +kwargs+, raising
        RecordNotFound if no such record exists.
        """
        result = self.where(**kwargs).first()
        if result:
            return result
        else:
            raise RecordNotFound(kwargs)

    @does_not_mutate
    def first(self, count=1):
        """
        Returns the first record in the query (sorting by id unless modified by
        `order_by`), returning None if the query has no records.
        """
        if count == 0:
            raise QueryInvalid("Count cannot be zero.")
        self.limit_count = count
        records = self._do_query().fetchall()
        if not records:
            return None
        if count == 1:
            record = records[0]
            args = dict(zip(self.attributes, record))
            return self.model.from_dict(**args)
        return self

    @does_not_mutate
    def last(self, count=1):
        """
        Returns the last record in the query (sorting by id unless modified by
        `order_by`, whereupon it reverses the order passed in `order_by`).
        Returns None if the query has no records.
        """
        if self._order_with:
            order = self._order_with.values()[0]
            order = "desc" if order == "asc" else "asc"
            order_with = self._order_with
            self._order_with = {}
            result = self.order_by(**{order_with.keys()[0]: order}).first(count)
            self._order_with = order_with
            return result
        else:
            return self.order_by(id="desc").first(count)

    @does_not_mutate
    def order_by(self, **kwargs):
        """
        Orders the query by the key passed in +kwargs+. Only pass one key, as
        it cannot sort by multiple columns at once. Raises QueryInvalid if this
        method is called when there is already a custom order (i.e. this
        method was already called on this query). Analog to "ORDER BY" in SQL.
        """
        # Only get one thing from kwargs (we can only order by one thing...)
        if self._order_with:
            raise QueryInvalid("Cannot order by more than one column")
        self._order_with = dict([kwargs.popitem()])
        return self

    @does_not_mutate
    def where(self, *custom_restrictions, **restrictions):
        """
        Restricts the records to the query subject to the passed
        +restrictions+. Analog to "WHERE" in SQL. Can pass multiple
        restrictions, and can invoke this method multiple times per query.
        """
        for attr, value in restrictions.items():
            self.where_query[attr] = value
        if custom_restrictions:
            self.custom_where.append(tuple(custom_restrictions))
        return self

    @does_not_mutate
    def joins(self, table):
        """
        Analog to "INNER JOIN" in SQL on the passed +table+. Use only once
        per query.
        """

        def do_join(table, model):
            while model is not associations.model_from_name(table):
                # ex) Category -> Forum -> Thread -> Post
                # Category: {"posts": "forums"}
                # Forum: {"posts": "threads"}
                # Thread: {"posts": None}
                # >>> Category.joins("posts")
                # => [
                #       {'table': 'forums', 'on': ['category_id', 'id']}
                #       {'table': 'threads', 'on': ['forum_id', 'id']}
                #       {'table': 'posts', 'on': ['thread_id', 'id']}
                #    ]
                if table in associations.associations_for(model):
                    # This to next: one-many (they have the fk)
                    # If associations.associations_for(model)[table] is None, then this is
                    # terminal (i.e. table is the FINAL association in the
                    # chain)
                    next_level = associations.associations_for(model)[table] or table
                    next_model = associations.model_from_name(next_level)
                    foreign_key = associations.foreign_keys_for(model).get(
                        next_level,
                        inflector.foreignKey(model.__name__))
                    yield {'table': next_level, 'on': [foreign_key, 'id']}
                else:
                    # One-One or Many-One
                    # singular table had better be in associations.associations_for(model)
                    singular = inflector.singularize(table)
                    next_level = associations.associations_for(model)[singular] or singular
                    next_model = associations.model_from_name(next_level)
                    this_table_name = Repo.table_name(model)
                    foreign_key = associations.foreign_keys_for(model).get(
                        next_level,
                        inflector.foreignKey(model.__name__))
                    if associations.model_has_foreign_key_for_table(table,
                                                                    model):
                        # we have the foreign key
                        order = ['id', foreign_key]
                    else:
                        # They have the foreign key
                        order = [foreign_key, 'id']
                    yield {'table': inflector.pluralize(next_level), 'on': order}
                model = next_model

        self.join_args = list(do_join(table, self.model))
        return self

    @does_not_mutate
    def group(self, column):
        """
        Applies a `GROUP BY` clause to the SQL generated by the Repo.
        """
        self.group_column = column
        return self

    @does_not_mutate
    def having(self, *conditions):
        """
        SQL uses the `HAVING` clause to specify conditions on the `GROUP BY`
        fields. Similarly, `having` allows specification of +conditions+ on
        fields chosen by `group`.

        >>> Order.all().group("date(created_at)").having("sum(price) > ?", 10)
        """
        self.having_args.append(tuple(conditions))
        return self

    @does_not_mutate
    def select(self, *fields):
        """
        Limit the number of fields accessed by SQL to those passed in
        +fields+.
        """
        self.attributes = fields
        return self

    def _query_repo(self):
        repo = Repo(self.table)
        if self.where_query or self.custom_where:
            repo = repo.where(self.custom_where, **self.where_query)
        if self.join_args:
            repo = repo.inner_join(*self.join_args)
        if self._order_with:
            repo = repo.order_by(**self._order_with)
        if self.group_column:
            repo = repo.group_by(self.group_column)
        if self.having_args:
            repo = repo.having(self.having_args)
        if self.limit_count:
            repo = repo.limit(self.limit_count)
        return repo

    def _do_query(self):
        return self._query_repo().select(*self.attributes)

    def __iter__(self):
        result = self._do_query().fetchall()
        for record in result:
            args = dict(zip(self.attributes, record))
            yield self.model.from_dict(**args)

    def __len__(self):
        result = self._query_repo().count()
        return result.fetchone()[0]

    def __repr__(self):
        return "<{name} {records}>".format(
            name="lazy_record.Query",
            records=list(self)
        )

    def create(self, **attributes):
        """
        Creates a new record suject to the restructions in the query and with
        the passed +attributes+. Operates using `build`.
        """
        record = self.build(**attributes)
        record.save()
        return record

    def build(self, **kwargs):
        """
        Builds a new record subject to the restrictions in the query.
        Will build intermediate (join table) records as needed, and links them
        to the returned record so that they are saved when the returned record
        is.
        """
        build_args = dict(self.where_query)
        build_args.update(kwargs)
        record = self.model(**record_args(build_args))
        if self.join_args:
            # EXAMPLE:
            # Say we have a many-to-many relation like so:
            #   Post -> Tagging -> Tag
            # If we are adding a tag to a post, we need to create the tagging
            # in addition to the tag. To do this, we add a "related record" to
            # the tag which is the tagging. By building the previous record,
            # if it exists, we can recursively build a long object tree.
            # That is, when we do post.tags(), we get a query that looks like:
            # Query(Tag).joins("taggings").where(taggings={"post_id":post.id})
            # The call to "build" then creates a tag using kwargs and the where
            # constraint, and creates a tagging that looks like:
            # Tagging(post_id = post.id) and adds it to the tag's related
            # records. The tagging's tag_id is added once the tag is saved
            # which is the first time it gets an id
            # Join args will never have just one element
            next_to_build = getattr(self.record, self.join_args[-2]['table']).build()
            record._related_records.append(next_to_build)
        return record

    def append(self, record):
        """
        Adds the passed +record+ to satisfy the query. Only intended to be
        used in conjunction with associations (i.e. do not use if self.record
        is None).

        Intended use case (DO THIS):

        post.comments.append(comment)

        NOT THIS:

        Query(Post).where(content="foo").append(post)
        """
        if self.record:
            self._validate_record(record)
            if self.join_args:
                # As always, the related record is created when the primary
                # record is saved
                build_args = dict(self.where_query)
                # The +final_join+ is what connects the record chain to the
                # passed +record+
                final_join = self.join_args[-2]
                # don't need to worry about one-to-many through because
                # there is not enough information to find or create the
                # joining record
                # i.e. in the Forum -> Thread -> Post example
                # forum.posts.append(post) doesn't make sense since there
                # is no information about what thread it will be attached to
                # Thus, this only makes sense on many-to-many. BUT we still
                # have to consider the case where there is a one-many-many
                # To make that work, we need to treat this like when doing
                # building
                joining_relation = getattr(self.record, final_join['table'])
                # Uses the lookup info in the join to figure out what ids to
                # set, and where to get the id value from
                joining_args = {final_join['on'][0]:
                                getattr(record, final_join['on'][1])}
                build_args.update(joining_args)
                joining_record = joining_relation.build(**build_args)
                self.record._related_records.append(joining_record)
            else:
                # Add our id to their foreign key so that the relationship is
                # created
                setattr(record,
                        foreign_key(record, self.record),
                        self.record.id)
                # Add to the list of related records so that it is saved when
                # we are
                self.record._related_records.append(record)

    def delete(self, record):
        """
        Removes a record from an query. Does not destroy the passed +record+,
        but marks any joining records for destruction (in the case of a
        many-to-many relationship) or sets the foreign key of +record+ to None
        (in the case of a one-to-many relationship). Only intended to be
        used in conjunction with associations (i.e. do not use if self.record
        is None).
        """
        # note: does (and should) not delete or destroy the record
        if self.record:
            self._validate_record(record)
            if self.join_args:
                # Need to find out who has the foreign key
                # If record has it, set to None, then done.
                # If one level up has it, mark the record for destruction
                final_table = self.join_args[0]['table']
                if final_table in associations.associations_for(self.model):
                    # +record+ does not have the foreign key
                    # Find the record one level up, then mark for destruction
                    related_class = associations.model_from_name(
                        final_table)
                    related_record = related_class.find_by(
                        **self._related_args(record, related_class))
                    # mark the joining record to be destroyed the primary is saved
                    self.record._delete_related_records.append(related_record)
                else:
                    # We have the foreign key
                    # Look up in the foreign key table, bearing in mind that
                    # this is a belongs_to, so the entry will be singular,
                    # whereas the table name is plural (we need to remove the
                    # 's' at the end)
                    key = associations.foreign_keys_for(self.model
                            )[inflector.singularize(final_table)]
                    # Set the foreign key to None to deassociate
                    setattr(record, key, None)
            else:
                setattr(record, foreign_key(record, self.record), None)
                # Ensure that the change is persisted on save
                self.record._related_records.append(record)

    def _related_args(self, record, related_class):
        # Both records are already persisted (have ids), so we can
        # set up the relating record fully now. One of the ids comes
        # from the constraint on the query, the other comes from
        # the foreign key logic below:
        # What we do is we get the singular table name of the record.
        # With that, we can look into the related class description for
        # the correct foreign key, which is set to the passed record's
        # id.
        record_class_name = inflector.singularize(Repo.table_name(record.__class__))
        related_args = self.where_query.get(Repo.table_name(related_class), {})
        related_key = associations.foreign_keys_for(related_class)[record_class_name]
        related_args[related_key] = record.id
        return related_args

    def _validate_record(self, record):
        if record.__class__ != self.model:
            raise AssociationTypeMismatch(
                "Expected record of type {expected}, got {actual}.".format(
                    expected=self.model.__name__,
                    actual=record.__class__.__name__
                ))

    def __getattr__(self, attr):
        # Check to see if there is a scope with this name on the queried model
        if attr in self.model.__scopes__:
            # Grab the scope lambda
            scope = self.model.get_scope(attr)
            # Bind the lambda to self so it acts like a method
            bound_scope = types.MethodType(scope, self)
            # Define the method on self
            setattr(self, attr, bound_scope)
            # Try again. This time, it will find the attribute, so __getattr__
            # will not get called again
            return getattr(self, attr)
        else:
            # Not a scope: resume standard attribute lookup
            return self.__getattribute__(attr)

    class __metaclass__(type):
        def __repr__(self):
            return "<class 'lazy_record.Query'>"


def foreign_key(local, foreign):
    local_class = local.__class__
    foreign_class = foreign.__class__
    return associations.foreign_keys_for(local_class
        )[inflector.singularize(Repo.table_name(foreign_class))]

def record_args(arg_dict):
    return {key: value
            for key, value in arg_dict.items()
            if type(value) is not dict}

# Here to prevent circular import loop
from lazy_record.errors import *
import lazy_record.associations as associations
