# lazy_record
Generic Model Layer for Python Web Applications using Sqlite3

[![Build Status](https://travis-ci.org/ECESeniorDesign/lazy_record.svg?branch=master)](https://travis-ci.org/ECESeniorDesign/lazy_record)
[![Code Climate](https://codeclimate.com/github/ECESeniorDesign/lazy_record/badges/gpa.svg)](https://codeclimate.com/github/ECESeniorDesign/lazy_record)
[![Coverage Status](https://coveralls.io/repos/ECESeniorDesign/lazy_record/badge.svg?branch=master&service=github)](https://coveralls.io/github/ECESeniorDesign/lazy_record?branch=master)

# Usage

To make the behavior of lazy_record avaliable, add the following into any files in which you define models:

```python
import lazy_record
from lazy_record.associations import *
```

The first line makes lazy_record avaliable within your scope, and the second line makes the association decorators
`has_many` and `belongs_to` avaliable. You could neglect to add the second line, and instead use `lazy_record.associations.has_many`.

# Models

Lazy Record Models inherit from `lazy_record.Base`. Furthermore, they need to define the `__attributes__` class variable to
reflect their database schema (it is assumed empty if not defined). An example schema and model is included below:

```sql
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

```python
class Entry(lazy_record.Base):
    __attributes__ = {
        "name": str
    }
```

## Saving and Querying

Lazy Record exposes convience methods for querying records. Using the example above, you can do the following:

```python
>>> entry = Entry(name="foo")
>>> entry.save()
>>> Entry.all()
<lazy_record.Query [Entry(id=1, name="foo", created_at=2016-01-08 01:53:45, updated_at=2016-01-08 01:53:45)]>
>>> Entry.where(name="bar")
<lazy_record.Query []>
>>> Entry.where("name LIKE ?", "bar")
<lazy_record.Query []>
```

Methods that return queries (`where`, `all`, `joins`) can be chained, so something like this is valid:

```python
Entry.where(name="foo").where(id=7)
```

## Validations

Validations can be added by defining a `__validates__` class variable to the model. This variable is a dictionary
whose keys are column names, and whose values are functions that return `True` when the validation passes, and `False`
if the validation fails.
Some common validations can be found in `lazy_record.validations`.

Example (validate name is all lowercase):

```python
class Entry(lazy_record.Base):
    __attributes__ = {
        "name": str
    }
    __validates__ = {
        "name": lambda record: record.name == record.name.lower()
    }
```

Attempts to save an invalid record will raise `lazy_record.RecordInvalid`.

## Associations

The decorators `@has_many` and `@belongs_to` can be used to define relationships between records.

```python
@belongs_to("post")
class Comment(lazy_record.Base):
    ...

@has_many("comments")
class Post(lazy_record.Base):
    ...
```

This allows the querying and creation of related records.

```python
>>> post = Post()
>>> post.save()
>>> comment = post.comments.build()
>>> comment.save()
>>> post.comments
<lazy_record.Query [Comment(id=1, created_at=2016-01-08 01:53:45, updated_at=2016-01-08 01:53:45, post_id=1)]>
```

Currently, one-to-many and many-to-many relationships are supported, and the foreign keys can be changed for one-to-many
relationships. Many-to-many relationships require the creation of a joining table (and model), and to pass the keyword
`through` to the `@has_many` decorator that is the name of the joining table.

# Connecting to a Database

To connect lazy_record to a database, call `lazy_record.connect_db`, passing the path to the database. The connection can
be closed by calling `lazy_record.close_db()`.
