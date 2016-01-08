from query import Query
from lazy_record.errors import *


class QueryMethods(object):

    @classmethod
    def find(cls, id):
        """
        Find record by +id+, raising RecordNotFound if no record exists.
        """
        return cls.find_by(id=id)

    @classmethod
    def find_by(cls, **kwargs):
        """
        Find first record subject to restrictions in +kwargs+, raising
        RecordNotFound if no such record exists.
        """
        result = Query(cls).where(**kwargs).first()
        if result:
            return result
        else:
            raise RecordNotFound(kwargs)

    @classmethod
    def all(cls):
        """
        Returns a Query object of all records in this classes table.
        """
        return Query(cls).all()

    @classmethod
    def where(cls, *args, **kwargs):
        """
        Returns a Query object of all records in this classes table, subject
        to the restrictions in +kwargs+. More advanced queries can be passed
        in the form:

        >>> MyClass.where("name LIKE ?", "foo")
        """
        return Query(cls).where(*args, **kwargs)

    @classmethod
    def joins(cls, table):
        """
        Returns a Query object of all records in this classes table with
        matching ids to foreign keys in +table+.
        """
        return Query(cls).joins(table)

    @classmethod
    def first(cls):
        """
        Returns the first record in the table, ordered by id, returning None
        if no records exist.
        """
        return Query(cls).first()

    @classmethod
    def last(cls):
        """
        Returns the last record in the table, ordered by id, returning None
        if no records exist.
        """
        return Query(cls).last()
