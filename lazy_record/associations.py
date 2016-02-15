import query
import repo
from lazy_record.errors import *
from inflector import Inflector, English

inflector = Inflector(English)

models = {}
associations = {}
foreign_keys = {}
scopes = {}

def model_from_name(parent_name):
    return models[inflector.classify(parent_name)]

def _verify_type_match(record, association):
    associated_model = model_from_name(association)
    if record is None:
        return
    if not isinstance(record, associated_model):
        raise AssociationTypeMismatch(
            "Expected record of type {expected}, got {actual}.".format(
                expected=associated_model.__name__,
                actual=record.__class__.__name__
            ))

def model_has_foreign_key_for_table(table, model):
    fk = foreign_keys_for(model).get(inflector.singularize(table), None)
    if fk is None:
        return True
    return fk in model.__attributes__

def foreign_keys_for(klass):
    if type(klass) == str:
        klass_name = klass
    else:
        klass_name = klass.__name__
    foreign_keys[klass_name] = foreign_keys.get(klass_name, {})
    return foreign_keys[klass_name]

def associations_for(klass):
    if type(klass) == str:
        klass_name = klass
    else:
        klass_name = klass.__name__
    associations[klass_name] = associations.get(klass_name, {})
    return associations[klass_name]

def scopes_for(klass):
    klass_name = klass.__name__
    scopes[klass_name] = scopes.get(klass_name, {})
    return scopes[klass_name]

class belongs_to(object):
    """
    Decorator to establish this model as the child in a one-to-many
    relationship.
    """
    def __init__(self, parent_name, foreign_key=None):
        """
        +parent_name+ is the parent model (e.g. if a post has many comments,
        the comment will have one post: post is the +parent_name+).
        +foreign_key+ is the foreign key used in the child (this) record to
        hold the id of the parent record. By default it is the parent's model
        name, snake-cased, with "_id" appended (e.g. Post -> "post_id").

        Creates a setter and getter property for the parent record.

        ex)

        >>> comment.post_id
        1
        >>> comment.post
        Post(id=1)
        >>> other_post
        Post(id=1)
        >>> comment.post = other_post
        >>> comment.post
        Post(id=2)
        >>> comment.post_id
        2
        """
        self.parent_name = parent_name
        self.foreign_key = foreign_key or inflector.foreignKey(parent_name)

    def __call__(self, klass):
        # Add the model to the registry of known models with associations
        models[klass.__name__] = klass
        # Set the foreign key in the model in case it needs to be looked up
        foreign_keys_for(klass)[self.parent_name] = self.foreign_key
        # Add the relationship to the association list
        associations_for(klass)[self.parent_name] = None

        # Getter method for the parent record (e.g. comment.post)
        # Is added to the class as a property
        def parent_record_getter(wrapped_obj):
            parent = model_from_name(self.parent_name)
            # Not using parent.find() because it raises if it cannot find
            q = query.Query(parent)
            return q.where(id=getattr(wrapped_obj, self.foreign_key)).first()

        # Setter method for updating the foreign key in this object
        def parent_record_setter(wrapped_obj, new_parent):
            if new_parent is not None:
                _verify_type_match(new_parent, self.parent_name)
                # We are setting a parent: grab it's id and use it
                setattr(wrapped_obj, self.foreign_key, new_parent.id)
            else:
                # Un-setting a parent, set the foreign key to None
                # Can't use new_parent.id since new_parent is None
                setattr(wrapped_obj, self.foreign_key, None)

        # Add setter and getter to class as properties
        setattr(klass, self.parent_name,
                property(parent_record_getter, parent_record_setter))
        # Add the foreign key to the attribute dict of the model
        # Doing so in such a way as to not mutate the dict, otherwise it can
        # override the value in lazy_record.Base (and thus all models)
        new_attributes = dict(klass.__attributes__)
        new_attributes[self.foreign_key] = int
        klass.__attributes__ = new_attributes
        return klass


# Currently exists only so that all models get registered
class has_many(object):
    """
    Decorator to establish this model as the parent in a one-to-many
    relationship or as one part of a many-to-many relationship
    """
    def __init__(self, child_name, scope=lambda query: query,
                 foreign_key=None, through=None):
        """
        +child_name+ is the child model (e.g. if a post has many comments:
        comments is the +child_name+). +foreign_key+ is the foreign key used in
        the child (this) record to hold the id of the parent record. By default
        it is the parent's model name, snake-cased, with "_id" appended
        (e.g. Post -> "post_id"). If this is a many-to-many relationship,
        +through+ is the joining table.

        Creates a getter property for child records and (if applicable the
        joining records).

        ex)

        >>> post.comments
        <lazy_record.Query [Comment(id=1)]>
        """
        self.child_name = child_name
        self.foreign_key = foreign_key
        self.through = through
        self.scope = scope

    def __call__(self, klass):
        self.klass = klass
        our_name = inflector.singularize(repo.Repo.table_name(klass))
        child_model_name = inflector.classify(self.child_name)
        scopes_for(klass)[self.child_name] = self.scope
        # If we are doing an implicit has_many using through, we should define it fully
        if self.through and self.through not in associations_for(klass):
            klass = has_many(self.through)(klass)
        if self.through and self.through not in associations_for(child_model_name):
            # Set up the association for the child
            # Assume a one-many tree unless already defined otherwise
            associations_for(child_model_name)[our_name] = \
                inflector.singularize(self.through)
        # if no foreign key was passed, we should calculate it now based on
        # the class name
        self.foreign_key = self.foreign_key or inflector.foreignKey(our_name)
        models[klass.__name__] = klass
        # Add the foreign key to the fk list
        if not self.through:
            foreign_keys_for(klass)[self.child_name] = self.foreign_key
            # Add the childs associations and foreign keys as if they had
            # a belongs_to
            foreign_keys_for(child_model_name)[our_name] = self.foreign_key
            associations_for(child_model_name)[our_name] = None
            
        # Add the relationship to the association list
        associations_for(klass)[self.child_name] = self.through

        # Add the child table (or joining table) to the classes dependents
        # so that if this record is destroyed, all related child records
        # (or joining records) are destroyed with it to prevent orphans
        if self.through:
            if self.through in foreign_keys_for(klass):
                klass.__dependents__ = klass.__dependents__ + [self.through]
        else:
            klass.__dependents__ = klass.__dependents__ + [self.child_name]
        if self.through:

            # Do the query with a join
            def child_records_method(wrapped_obj):
                child = model_from_name(self.child_name)
                # No guarentee that self.through is the last in the chain
                # It could be the other part of a many-to-many
                # Or it could be a through that is a couple of levels down
                # e.g. Category has many Posts through Threads
                #      (but chain is Category -> Forum -> Thread -> Post)
                result = query.Query(child, record=wrapped_obj).joins(
                            repo.Repo.table_name(wrapped_obj.__class__)).where(
                            **{repo.Repo.table_name(wrapped_obj.__class__):
                            {'id': wrapped_obj.id}})
                return self.scoping(result)
        else:
            # Don't do a join
            def child_records_method(wrapped_obj):
                child = model_from_name(self.child_name)
                q = query.Query(child, record=wrapped_obj)
                where_statement = {self.foreign_key: wrapped_obj.id}
                return self.scoping(q.where(**where_statement))

        setattr(klass, self.child_name, property(child_records_method))
        return klass

    def scoping(self, query):
        current = self.klass
        scopes = []
        while True:
            # Anything other than a has_many won't have an entry,
            # so we return the identity scope
            scopes.append(scopes_for(current).get(self.child_name,
                                                  lambda query: query))
            # Should give either a joining model or None
            # TODO handle case for has_one
            # currently, only has_many_supports scoping
            joiner = associations_for(current).get(self.child_name)
            # End of the line
            if joiner is None:
                break
            # Get the next in the list by looking at the joiner model
            current = model_from_name(joiner)
        for scope in scopes:
            query = scope(query)
        return query

class has_one(object):
    """
    Decorator to establish this model as the parent in a one-to-one
    relationship.
    """
    def __init__(self, child_name, foreign_key=None, through=None):
        self.child_name = child_name
        self.foreign_key = foreign_key
        self.through = through
        if str(self.through).endswith('s'):
            raise AssociationForbidden(
                "Cannot have one '{}' through many '{}'".format(
                    self.child_name,
                    self.through,
                ))

    def __call__(self, klass):
        our_name = inflector.singularize(repo.Repo.table_name(klass))
        child_model_name = inflector.classify(self.child_name)
        self.foreign_key = self.foreign_key or inflector.foreignKey(our_name)
        klass.__dependents__ = klass.__dependents__ + [self.child_name]
        # Add the relationship to the association list
        associations_for(klass)[self.child_name] = self.through
        # Add the foreign key to the fk list
        foreign_keys_for(klass)[self.child_name] = self.foreign_key
        models[klass.__name__] = klass
        if self.through and self.through not in associations_for(child_model_name):
            # Set up the association for the child
            # Assume a one-many tree unless already defined otherwise
            associations_for(child_model_name)[our_name] = self.through

        if self.through:

            def child_record_method(wrapped_obj):
                child = model_from_name(self.child_name)
                return query.Query(child, record=wrapped_obj).joins(
                          repo.Repo.table_name(wrapped_obj.__class__)).where(
                          **{repo.Repo.table_name(wrapped_obj.__class__):
                              {'id': wrapped_obj.id}}).first()

            def set_child_record_method(wrapped_obj, new_value):
                _verify_type_match(new_value, self.child_name)
                child = model_from_name(self.child_name)
                table = repo.Repo.table_name(wrapped_obj.__class__)
                q = query.Query(child, record=wrapped_obj).joins(table
                        ).where(**{table: {'id': wrapped_obj.id}})
                # Get the previous value
                old_value = q.first()
                # Recall that join_args will have either 0 or 2 or more,
                # never 1 element
                joiner = q.join_args[-2]
                # Find the intermediate record that will connect +new_value+
                # to wrapped_obj
                next_up = model_from_name(joiner['table'])
                next_r = query.Query(next_up, record=wrapped_obj).joins(
                             table).where(**{table: {'id': wrapped_obj.id}}
                             ).first()
                if not model_has_foreign_key_for_table(joiner['table'],
                                                       child):
                    # The intermediate record has the foreign key: set it
                    if new_value is None:
                        setattr(next_r,
                                joiner['on'][0],
                                None)
                    else:
                        setattr(next_r,
                                joiner['on'][0],
                                getattr(new_value, joiner['on'][1]))
                    wrapped_obj._related_records.append(next_r)
                else:
                    # Set the foreign key on the new value
                    if new_value is not None:
                        # Associate new value
                        setattr(new_value,
                                joiner['on'][1], # Foreign key
                                # Lookup the id/foreign_key of the record
                                getattr(next_r, joiner['on'][0]))
                        wrapped_obj._related_records.append(new_value)
                    # Disassociate the old value
                    if old_value is not None:
                        setattr(old_value,
                                joiner['on'][1], # Foreign key
                                None)
                        wrapped_obj._related_records.append(old_value)

        else:

            def child_record_method(wrapped_obj):
                child = model_from_name(self.child_name)
                q = query.Query(child, record=wrapped_obj)
                where_statement = {self.foreign_key: wrapped_obj.id}
                return q.where(**where_statement).first()

            def set_child_record_method(wrapped_obj, child):
                _verify_type_match(child, self.child_name)
                # We are setting a child: set its foreign key to our id
                if child is not None:
                    setattr(child, self.foreign_key, wrapped_obj.id)
                    wrapped_obj._related_records.append(child)
                # disassociate old record
                old_value = child_record_method(wrapped_obj)
                if old_value is not None:
                    setattr(old_value, self.foreign_key, None)
                    wrapped_obj._related_records.append(old_value)

        setattr(klass, self.child_name, property(child_record_method,
                                                 set_child_record_method))
        return klass
