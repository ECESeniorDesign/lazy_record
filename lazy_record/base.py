from query import Query
from repo import Repo
import datetime
from errors import *

class Base(object):
    __attributes__ = {}
    __validates__ = {}
    def __init__(self, **kwargs):
        if set(["id", "created_at"]) & set(kwargs):
            raise AttributeError("Cannot set 'id' or 'created_at'")
        for attr in self.__class__.__attributes__:
            setattr(self, "_" + attr, None)
        for attr, val in kwargs.items():
            if attr in (list(self.__class__.__attributes__)):
                setattr(self, attr, val)
        self._id = None
        self._created_at = None
        self.__table = Repo.table_name(self.__class__)

    def __getattr__(self, attr):
        if attr == "id":
            if self._id:
                return self._id
            else:
                return None
        elif attr == "created_at":
            return self._created_at
        elif attr in self.__class__.__attributes__:
            value = self.__getattribute__("_" + attr)
            if value is not None:
                return self.__class__.__attributes__[attr](value)
            else:
                return None
        else:
            return self.__getattribute__(attr)

    def __setattr__(self, name, value):
        if name in ("id", "created_at"):
            raise AttributeError("Cannot set '{}'".format(name))
        elif name in self.__class__.__attributes__:
            setattr(self, "_" + name, self.__class__.__attributes__[name](value))
        else:
            super(Base, self).__setattr__(name, value)

    @classmethod
    def from_dict(cls, **kwargs):
        obj = cls()
        for attr, val in kwargs.items():
            setattr(obj, "_" + attr, val)
        return obj

    def delete(self):
        if self.id:
            Repo(self.__table).where(id=self.id).delete()

    def save(self):
        self.validate()
        if self.id:
            attrs = list(self.__class__.__attributes__) + ["created_at"]
            data = { attr: getattr(self, attr) for attr in attrs }
            Repo(self.__table).where(id=self.id).update(**data)
        else:
            attrs = list(self.__class__.__attributes__) + ["created_at"]
            self._created_at = datetime.date.today()
            data = { attr: getattr(self, attr) for attr in attrs }
            self._id = int(Repo(self.__table).insert(**data))

    def validate(self):
        reason = {}
        valid = True
        for attr, validation in self.__class__.__validates__.items():
            if not validation(getattr(self, attr)):
                reason[attr] = getattr(self, attr)
                valid = False
        if not valid:
            raise RecordInvalid(reason)

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

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(
                "{}={!r}".format(attr, getattr(self, attr))
                for attr in ["id"] + list(self.__class__.__attributes__) + [
                    "created_at"
                ]
                if hasattr(self, attr)))
