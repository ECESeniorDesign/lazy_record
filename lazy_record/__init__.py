__author__ = "Chase Conklin"

from query import Query
from repo import Repo
from base import Base
from errors import *
from types import *

def connect_db(database_name=":memory:"):
    """
    Connect lazy_record to the database at the path specified in
    +database_name+.
    """
    db = repo.Repo.connect_db(database_name)
    base.Repo.db = db
    query.Repo.db = db
    Repo.db = db

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
    Repo.db = None
