__author__ = "Chase Conklin"

from query import Query
from repo import Repo
from base import Base
from exceptions import *
from types import *

def connect_db(database_name=":memory:"):
    db = repo.Repo.connect_db(database_name)
    base.Repo.db = db
    query.Repo.db = db
    Repo.db = db
