import query
import repo
models = {}

def model_from_name(parent_name):
    class_name = "".join(
        name.title() for name in parent_name.split("_")
    )
    return models[class_name]

class belongs_to(object):
    def __init__(self, parent_name, foreign_key=None):
        self.parent_name = parent_name
        self.foreign_key = foreign_key or "{name}_id".format(
            name=self.parent_name)
    def __call__(self, klass):
        models[klass.__name__] = klass
        klass.__foreign_keys__[self.parent_name] = self.foreign_key
        def parent_record_getter(wrapped_obj):
            parent = model_from_name(self.parent_name)
            q = query.Query(parent)
            return q.where(id=getattr(wrapped_obj, self.foreign_key)).first()
        def parent_record_setter(wrapped_obj, new_parent):
            if new_parent is not None:
                setattr(wrapped_obj, self.foreign_key, new_parent.id)
            else:
                setattr(wrapped_obj, self.foreign_key, None)
        setattr(klass, self.parent_name,
            property(parent_record_getter, parent_record_setter))
        new_attributes = dict(klass.__attributes__)
        new_attributes[self.foreign_key] = int
        klass.__attributes__ = new_attributes
        return klass

# Currently exists only so that all models get registered
class has_many(object):
    def __init__(self, child_name, foreign_key=None, through=None):
        self.child_name = child_name
        self.foreign_key = foreign_key
        self.through = through
    def __call__(self, klass):
        # if no foreign key was passed, we should calculate it now based on
        # the class name
        self.foreign_key = self.foreign_key or "{name}_id".format(
            name=repo.Repo.table_name(klass)[:-1])
        models[klass.__name__] = klass
        klass.__foreign_keys__[self.child_name] = self.foreign_key
        if self.through:
            klass.__dependents__ = klass.__dependents__ + [self.through]
        else:
            klass.__dependents__ = klass.__dependents__ + [self.child_name]
        if self.through:
            # Do the query with a join
            def child_records_method(wrapped_obj):
                child = model_from_name(self.child_name[:-1])
                q = query.Query(child, record=wrapped_obj).joins(self.through)
                where_statement = {self.through:
                    {self.foreign_key: wrapped_obj.id}}
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
