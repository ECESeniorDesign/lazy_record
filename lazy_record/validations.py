"""
Module of common validation functions used to validate records.
"""

__all__ = ["present", "unique", "absent", "length", "validation"]

class validation(object):

    def __init__(self, fun):
        self.fun = fun

    def __call__(self, record, name=None):
        return self.fun(record, name or self.name)

@validation
def present(record, name):
    return bool(getattr(record, name))

@validation
def absent(record, name):
    return not present(record, name)

@validation
def unique(record, name):
    model = record.__class__
    others = model.where("id IS NOT ?", record.id
                 ).where("{} == ?".format(name), getattr(record, name))
    return len(list(others)) == 0

def length(within):
    @validation
    def length_validator(record, name):
        return len(getattr(record, name)) in within
    return length_validator
