from .query import Query
from .base import Base
from .errors import *
from .typecasts import *
from .schema import Schema

__author__ = "Chase Conklin"


def connect_db(database_name=":memory:"):
    """
    Connect lazy_record to the database at the path specified in
    +database_name+.
    """
    db = repo.Repo.connect_db(database_name)
    base.Repo.db = db
    query.Repo.db = db


def close_db():
    """
    Close the connection to the database opened in `connect_db`
    """
    db = repo.Repo.db
    if db is not None:
        db.close()
    repo.Repo.db = None
    base.Repo.db = None
    query.Repo.db = None

def load_schema(sch):
    """
    Load a schema object.
    """
    schema.tables = {}
    schema.load(sch)

def execute_schema(sch):
    """
    Load a schema object.
    """
    schema.tables = {}
    schema.execute(sch)