from query import Query
from errors import *
class QueryMethods(object):
    @classmethod
    def find(cls, id):
        result = Query(cls).where(id=id).first()
        if result:
            return result
        else:
            raise RecordNotFound({'id': id})

    @classmethod
    def find_by(cls, **kwargs):
        result = Query(cls).where(**kwargs).first()
        if result:
            return result
        else:
            raise RecordNotFound(kwargs)

    @classmethod
    def all(cls):
        return Query(cls).all()

    @classmethod
    def where(cls, **kwargs):
        return Query(cls).where(**kwargs)

    @classmethod
    def joins(cls, table):
        return Query(cls).joins(table)

    @classmethod
    def first(cls):
        return Query(cls).first()

    @classmethod
    def last(cls):
        return Query(cls).last()
