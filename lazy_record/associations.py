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

# TODO fully implement
# Currently exists only so that all models get registered
class has_many(object):
    def __init__(self, child_name):
        self.child_name = child_name
    def __call__(self, klass):
        models[klass.__name__] = klass
        return klass