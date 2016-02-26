import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from query import Query
from repo import Repo
import datetime
from lazy_record.errors import *
import lazy_record.typecasts as typecasts
from validations import Validations
import lazy_record.associations as associations
from itertools import chain
from inflector import Inflector, English

inflector = Inflector(English)


class Base(Validations):
    __attributes__ = {}
    __dependents__ = []
    __scopes__ = {}

    def __init__(self, **kwargs):
        """
        Instantiate a new object, mass-assigning the values in +kwargs+.
        Cannot mass-assign id or created_at.
        """
        if set(["id", "created_at", "updated_at"]) & set(kwargs):
            raise AttributeError("Cannot set 'id', 'created_at', "
                                 "or 'updated_at'")
        for attr in self.__class__.__all_attributes__:
            setattr(self, "_" + attr, None)
        self.update(**kwargs)
        self._id = None
        self.__table = Repo.table_name(self.__class__)
        self._related_records = []
        self._delete_related_records = []

    def __getattr__(self, attr):
        """
        Get and cast +attr+ according to the __attributes__ class variable.

        ex)
        >>> class MyRecord(lazy_record.Base)
        ...     __attributes__ = {
        ...         "my_val": int
        ...     }
        ...
        >>> record = MyRecord(my_val='11')
        >>> record.my_val
        11
        """
        def identity(val): return val
        attr_dict = self.__class__.__all_attributes__
        if attr in attr_dict or attr == "id":
            try:
                value = self.__getattribute__("_" + attr)
                if value is not None:
                    return attr_dict.get(attr, identity)(value)
                else:
                    return None
            except AttributeError:
                raise MissingAttributeError(
                    "'{}' object has no attribute '{}'".format(
                    self.__class__.__name__, attr))
        else:
            return self.__getattribute__(attr)

    def __setattr__(self, name, value):
        """
        Cast +value+ according to the __attributes__ class variable, then set
        the attribute +name+ to the casted value.

        ex)
        >>> class MyRecord(lazy_record.Base)
        ...     __attributes__ = {
        ...         "my_val": int
        ...     }
        ...
        >>> record = MyRecord()
        >>> record.my_val = '11'
        >>> record._my_val # Don't actually do this in production code.
        11
        """
        if name in ("id", "created_at", "updated_at"):
            raise AttributeError("Cannot set '{}'".format(name))
        elif name in self.__class__.__attributes__:
            if value is not None:
                setattr(self, "_" + name,
                        self.__class__.__attributes__[name](value))
            else:
                setattr(self, "_" + name, None)
        else:
            super(Base, self).__setattr__(name, value)

    @classmethod
    def from_dict(cls, **kwargs):
        """
        Construct an object an mass-assign its attributes using +kwargs+,
        ignoring all protections of id and created_at. Intended for
        constructing objects already present in the database (i.e for use by
        methods such as find or within Query).
        """
        # Create the object
        obj = cls()
        # By default, objects are initialized with attribute values of None
        # We need to clear those out so that we get AttributeError on access
        for attr in cls.__all_attributes__:
            delattr(obj, "_" + attr)
        del obj._id
        # Set the attributes that were passed
        for attr, val in kwargs.items():
            setattr(obj, "_" + attr, val)
        return obj

    def update(self, **kwargs):
        """
        Mass-assign the attributes in +kwargs+ to the object, preventing
        attributes not in __attributes__ from being set.
        """
        for attr, val in kwargs.items():
            if attr in (list(self.__class__.__attributes__) + \
                        list(associations.associations_for(self.__class__))):
                setattr(self, attr, val)

    def delete(self):
        """
        Delete this record without deleting any dependent or child records.
        This can orphan records, so use with care.
        """
        if self.id:
            with Repo.db:
                Repo(self.__table).where(id=self.id).delete()

    def _do_destroy(self):
        Repo(self.__table).where(id=self.id).delete()
        for dependent in set(self.__class__.__dependents__):
            if dependent == inflector.singularize(dependent):
                child = getattr(self, dependent)
                if child:
                    child._do_destroy()
            else:
                for record in (getattr(self, dependent) or []):
                    record._do_destroy()

    def destroy(self):
        """
        Delete this record, while also destroying (i.e. calling destroy) on
        all dependents and children.
        """
        if self.id:
            with Repo.db:
                self._do_destroy()

    def _do_save(self):
        self.validate()
        self._updated_at = datetime.datetime.today()
        if self.id:
            attrs = list(self.__class__.__all_attributes__)
            data = {attr: getattr(self, "_" + attr) for attr in attrs}
            Repo(self.__table).where(id=self.id).update(**data)
        else:
            attrs = list(self.__class__.__all_attributes__)
            self._created_at = datetime.datetime.today()
            data = {attr: getattr(self, "_" + attr) for attr in attrs}
            self.__id = int(Repo(self.__table).insert(**data))

    def _finish_save(self):
        if not self.id:
            self._id = self.__id
        for record in self._related_records:
            if not record.id:
                record._id = record.__id
        self._related_records = []

    def save(self):
        """
        Save a record to the database, creating it if needed, updating it
        otherwise. Also saves related records (children and dependents) as
        needed.
        """
        with Repo.db:
            self._do_save()
            our_name = inflector.singularize(Repo.table_name(self.__class__))
            for record in self._related_records:
                if not self._id:
                    related_key = associations.foreign_keys_for(
                        record.__class__)[our_name]
                    setattr(record, related_key, self.__id)
                record._do_save()
            for record in self._delete_related_records:
                record._do_destroy()
        self._finish_save()

    def __cmp__(self, other):
        """
        Compare to other records.
        """
        if self is other:
            return 0
        elif self.__class__ != other.__class__:
            return cmp(self.__class__, other.__class__)
        elif self.id == None:
            return 1
        elif other.id == None:
            return -1
        else:
            return cmp(self.id, other.id)

    def __int__(self):
        """
        Cast record to int (returns id).
        """
        if self.id:
            return int(self.id)
        else:
            return 0

    def __repr__(self):

        def gettimestamp(obj, attr):
            if getattr(obj, attr):
                return str(getattr(obj, attr).replace(microsecond=0))

        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(chain(
                ("{}={!r}".format(attr, getattr(self, attr))
                for attr in ["id"] + list(self.__class__.__attributes__)
                if hasattr(self, attr)),

                ("{}={}".format(attr, gettimestamp(self, attr))
                for attr in ["created_at", "updated_at"]
                if hasattr(self, attr)))))


    class __metaclass__(type):
        def get_scope(cls, scope_name):
            """
            Retrieve a scope method defined in __scopes__ and set the name
            appropriately.
            """
            # Fetch the scope from the __scopes__ dictionary
            scope = cls.__scopes__[scope_name]
            # Since the scopes defined in __scopes__ are often lambdas
            # to give the name meaning under repr, change the name of the
            # function to "<scope>scope_name"
            scope.__name__ = "<scope>{}".format(scope_name)
            return scope

        @property
        def __all_attributes__(cls):
            attrs = dict(cls.__attributes__)
            attrs.update({
                "created_at": typecasts.datetime,
                "updated_at": typecasts.datetime,
            })
            return attrs

        def __len__(cls):
            return len(Query(cls).all())

        def __getattr__(cls, attr):
            # Is the attr a scope?
            if attr in cls.__scopes__:
                # The attribute is a scope: fetch it, then bind it to the class
                # This way, it is already defined on the class for the next
                # lookup.
                # Think of it like the method_missing + define_method idiom
                # in Ruby (this is the define_method part).
                # "classmethod" handles the binding of the first argument
                setattr(cls, attr, classmethod(cls.get_scope(attr)))
                # Having defined the method, look again: it will be found under
                # normal object lookup
                return getattr(cls, attr)
            elif hasattr(Query(cls), attr):
                return getattr(Query(cls), attr)
            else:
                # The attribute is not a scope: without __getattr__ defined,
                # the behavior would be to raise AttributeError, so that's what
                # we do here. Note that the ususal call to __getattribute__
                # won't work, since it is not define on the metaclass. "super"
                # won't work for the same reason.
                raise AttributeError("'{}' has no attribute '{}'".format(
                    cls.__name__, attr))
