import query
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
        def parent_record_method(wrapped_obj):
            parent = model_from_name(self.parent_name)
            q = query.Query(parent)
            return q.where(id=getattr(wrapped_obj, self.foreign_key)).first()
        parent_record_method.__name__ = self.parent_name
        class Association(object):
            pass
        setattr(Association, self.parent_name, parent_record_method)
        klass.__bases__ += (Association, )
        return klass

# Currently exists only so that all models get registered
class has_many(object):
    def __init__(self, child_name, foreign_key=None):
        self.child_name = child_name
        self.foreign_key = foreign_key
    def __call__(self, klass):
        # if no foreign key was passed, we should calculate it now based on
        # the class name
        self.foreign_key = self.foreign_key or "{name}_id".format(
            name=query.Query.table_name(klass)[:-1])
        models[klass.__name__] = klass
        def child_records_method(wrapped_obj):
            child = model_from_name(self.child_name[:-1])
            q = query.Query(child)
            where_statement = {self.foreign_key: wrapped_obj.id}
            return q.where(**where_statement)
        child_records_method.__name__ = self.child_name
        class Association(object):
            pass
        setattr(Association, self.child_name, child_records_method)
        klass.__bases__ += (Association, )
        return klass