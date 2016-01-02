from repo import Repo
import associations
from errors import *

class Query(object):

    def __init__(self, model, record=None):
        self.model = model
        self.record = record
        self.where_query = {}
        self.join_table = None
        self._order_with = {}
        self.attributes = ["id", "created_at"] + \
            list(self.model.__attributes__)
        self.table = Repo.table_name(self.model)

    def all(self):
        return self

    def first(self):
        record = self._do_query().fetchone()
        if not record:
            return None
        args = dict(zip(self.attributes, record))
        return self.model.from_dict(**args)

    def last(self):
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
        # Only get one thing from kwargs (we can only order by one thing...)
        if self._order_with:
            raise QueryInvalid("Cannot order by more than one column")
        self._order_with = dict([kwargs.popitem()])
        return self

    def where(self, **restrictions):
        for attr, value in restrictions.items():
            self.where_query[attr] = value
        return self

    def joins(self, table):
        self.join_table = table
        return self

    def _do_query(self):
        repo = Repo(self.table)
        if self.where_query:
            repo = repo.where(**self.where_query)
        if self.join_table:
            repo = repo.inner_join(self.join_table,
                on=[self.table[:-1] + "_id", "id"])
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
        build_args = dict(self.where_query)
        build_args.update(kwargs)
        record = self.model(**build_args)
        if self.join_table:
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
            related_class = associations.model_from_name(self.join_table[:-1])
            related_args = build_args.get(self.join_table, {})
            related_record = related_class(**related_args)
            record._related_records.append(related_record)
        return record

    def append(self, record):
        if self.record:
            if self.join_table:
                # As always, the related record is created when the primary
                # record is saved
                related_class = associations.model_from_name(
                    self.join_table[:-1])
                related_record = related_class(
                    **self._related_args(record, related_class))
                self.record._related_records.append(related_record)
            else:
                self.record._related_records.append(record)

    def delete(self, record):
        # note: does (and should) not delete or destroy the record
        if self.record:
            if self.join_table:
                related_class = associations.model_from_name(
                    self.join_table[:-1])
                # Same logic as append
                related_record = related_class.find_by(
                    **self._related_args(record, related_class))
                # mark the joining record to be destroyed the primary is saved
                self.record._delete_related_records.append(related_record)
            else:
                record_class_name = Repo.table_name(record.__class__)[:-1]
                foreign_key = record.__class__.__foreign_keys__[
                    record_class_name]
                setattr(record, foreign_key, None)
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
        related_args = self.where_query.get(self.join_table, {})
        record_class_name = Repo.table_name(record.__class__)[:-1]
        related_key = related_class.__foreign_keys__[record_class_name]
        related_args[related_key] = record.id
        return related_args

    class __metaclass__(type):
        def __repr__(self):
            return "<class 'lazy_record.Query'>"
