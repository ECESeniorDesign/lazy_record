from repo import Repo
import sys
import os
import types
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

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
        self.join_args = []
        self._order_with = {}
        self.attributes = ["id", "created_at"] + \
            list(self.model.__attributes__)
        self.table = Repo.table_name(self.model)

    def all(self):
        """
        Returns all records that match the query.
        """
        return self

    def first(self):
        """
        Returns the first record in the query (sorting by id unless modified by
        `order_by`), returning None if the query has no records.
        """
        record = self._do_query().fetchone()
        if not record:
            return None
        args = dict(zip(self.attributes, record))
        return self.model.from_dict(**args)

    def last(self):
        """
        Returns the last record in the query (sorting by id unless modified by
        `order_by`, whereupon it reverses the order passed in `order_by`).
        Returns None if the query has no records.
        """
        if self._order_with:
            order = self._order_with.values()[0]
            order = "desc" if order == "asc" else "asc"
            order_with = self._order_with
            self._order_with = None
            result = self.order_by(**{order_with.keys()[0]: order}).first()
            self._order_with = order_with
            return result
        else:
            return self.order_by(id="desc").first()

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

    def where(self, **restrictions):
        """
        Restricts the records to the query subject to the passed
        +restrictions+. Analog to "WHERE" in SQL. Can pass multiple
        restrictions, and can invoke this method multiple times per query.
        """
        for attr, value in restrictions.items():
            self.where_query[attr] = value
        return self

    def joins(self, table):
        """
        Analog to "INNER JOIN" in SQL on the passed +table+. Use only once
        per query.
        """

        def do_join(table, model):
            while model is not associations.model_from_name(table[:-1]):
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
                if table in model.__associations__:
                    # This to next: one-many (they have the fk)
                    # If model.__associations__[table] is None, then this is
                    # terminal (i.e. table is the FINAL association in the
                    # chain)
                    next_level = model.__associations__[table] or table
                    next_model = associations.model_from_name(next_level[:-1])
                    this_table_name = Repo.table_name(model)
                    foreign_key = model.__foreign_keys__.get(
                        next_level,
                        this_table_name[:-1] + "_id")
                    yield {'table': next_level, 'on': [foreign_key, 'id']}
                else:
                    # This to next: many-one (we have the fk)
                    foreign_key = model.__foreign_keys__.get(
                        table, table[:-1] + "_id")
                    yield {'table': table, 'on': ['id', foreign_key]}
                    next_model = associations.model_from_name(table[:-1])
                model = next_model

        self.join_args = list(do_join(table, self.model))
        return self

    def _do_query(self):
        repo = Repo(self.table)
        if self.where_query:
            repo = repo.where(**self.where_query)
        if self.join_args:
            repo = repo.inner_join(*self.join_args)
        if self._order_with:
            repo = repo.order_by(**self._order_with)
        return repo.select(*self.attributes)

    def __iter__(self):
        result = self._do_query().fetchall()
        for record in result:
            args = dict(zip(self.attributes, record))
            yield self.model.from_dict(**args)

    def __repr__(self):
        return "<{name} {records}>".format(
            name="lazy_record.Query",
            records=list(self)
        )

    def build(self, **kwargs):
        """
        Builds a new record subject to the restrictions in the query.
        Will build intermediate (join table) records as needed, and links them
        to the returned record so that they are saved when the returned record
        is.
        """
        build_args = dict(self.where_query)
        build_args.update(kwargs)
        record = self.model(**build_args)
        if self.join_args:
            # EXAMPLE:
            # Say we have a many-to-many relation like so:
            #   Post -> Tagging -> Tag
            # If we are adding a tag to a post, we need to create the tagging
            # in addition to the tag. To do this, we add a "related record" to
            # the tag which is the tagging. We build this tagging using the
            # restrictions to the tagging (the record in the `join_table`)
            # where query.
            # That is, when we do post.tags(), we get a query that looks like:
            # Query(Tag).joins("taggings").where(taggings={"post_id":post.id})
            # The call to "build" then creates a tag using kwargs and the where
            # constraint, and creates a tagging that looks like:
            # Tagging(post_id = post.id) and adds it to the tag's related
            # records. The tagging's tag_id is added once the tag is saved
            # which is the first time it gets an id
            relations = (arg['table'] for arg in self.join_args)
            record._related_records += [build_relation(relation, build_args)
                                        for relation in relations]
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
                final_join = self.join_args[0]
                final_join_args = build_args[final_join['table']]
                # don't need to worry about one-to-many through because
                # there is not enough information to find or create the
                # joining record
                # i.e. in the Forum -> Thread -> Post example
                # forum.posts.append(post) doesn't make sense since there
                # is no information about what thread it will be attached to
                final_join_args[final_join['on'][0]] = getattr(
                    record, final_join['on'][1])
                relations = (arg['table'] for arg in self.join_args)
                self.record._related_records += [
                    build_relation(relation, build_args)
                    for relation in relations]
                # self.record._related_records.append(related_record)
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
                if final_table in self.model.__associations__:
                    # +record+ does not have the foreign key
                    # Find the record one level up, then mark for destruction
                    related_class = associations.model_from_name(
                        final_table[:-1])
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
                    key = self.model.__foreign_keys__[final_table[:-1]]
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
        record_class_name = Repo.table_name(record.__class__)[:-1]
        related_args = self.where_query.get(Repo.table_name(related_class), {})
        related_key = related_class.__foreign_keys__[record_class_name]
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
    return local_class.__foreign_keys__[Repo.table_name(foreign_class)[:-1]]

def build_relation(relation, build_args):
    related_class = associations.model_from_name(relation[:-1])
    return related_class(**build_args[relation])

# Here to prevent circular import loop
from lazy_record.errors import *
import lazy_record.associations as associations
