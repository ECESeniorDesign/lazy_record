import query
import repo


models = {}


def model_from_name(parent_name):
    class_name = "".join(
        name.title() for name in parent_name.split("_")
    )
    return models[class_name]


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
        self.foreign_key = foreign_key or "{name}_id".format(
            name=self.parent_name)

    def __call__(self, klass):
        # Add the model to the registry of known models with associations
        models[klass.__name__] = klass
        # Set the foreign key in the model in case it needs to be looked up
        klass.__foreign_keys__ = dict(klass.__foreign_keys__)
        klass.__foreign_keys__[self.parent_name] = self.foreign_key
        # Add the relationship to the association list
        klass.__associations__ = dict(klass.__associations__)
        klass.__associations__[self.parent_name] = None

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
    def __init__(self, child_name, foreign_key=None, through=None):
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

    def __call__(self, klass):
        # if no foreign key was passed, we should calculate it now based on
        # the class name
        self.foreign_key = self.foreign_key or "{name}_id".format(
            name=repo.Repo.table_name(klass)[:-1])
        models[klass.__name__] = klass
        # Add the foreign key to the fk list
        klass.__foreign_keys__ = dict(klass.__foreign_keys__)
        klass.__foreign_keys__[self.child_name] = self.foreign_key
        # Add the relationship to the association list
        klass.__associations__ = dict(klass.__associations__)
        klass.__associations__[self.child_name] = self.through
        # Add the child table (or joining table) to the classes dependents
        # so that if this record is destroyed, all related child records
        # (or joining records) are destroyed with it to prevent orphans
        if self.through:
            klass.__dependents__ = klass.__dependents__ + [self.through]
        else:
            klass.__dependents__ = klass.__dependents__ + [self.child_name]
        if self.through:

            # Do the query with a join
            def child_records_method(wrapped_obj):
                child = model_from_name(self.child_name[:-1])
                q = query.Query(child, record=wrapped_obj).joins(self.through)
                where_statement = {
                    self.through: {self.foreign_key: wrapped_obj.id}}
                return q.where(**where_statement)

            # define the method for the through
            def through_records_method(wrapped_obj):
                through = model_from_name(self.through[:-1])
                return query.Query(through, record=wrapped_obj).where(
                    **{self.foreign_key: wrapped_obj.id})

            setattr(klass, self.through,
                    property(through_records_method))
        else:
            # Don't do a join
            def child_records_method(wrapped_obj):
                child = model_from_name(self.child_name[:-1])
                q = query.Query(child)
                where_statement = {self.foreign_key: wrapped_obj.id}
                return q.where(**where_statement)

        setattr(klass, self.child_name, property(child_records_method))
        return klass
