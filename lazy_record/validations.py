"""
Module of common validation functions used to validate records.
"""

__all__ = ["present", "unique", "absent", "length"]

def present(name):
    def validator(record):
        if getattr(record, name) is 0:
            return True
        return bool(getattr(record, name))
    return validator

def absent(name):
    def validator(record):
        return not present(name)(record)
    return validator

def unique(name):
    def validator(record):
        model = record.__class__
        others = model.where("id != ?", record.id
                     ).where("{} == ?".format(name), getattr(record, name))
        return len(list(others)) == 0
    return validator

def length(within):
    def length_validator(name):
        def validator(record):
            return len(getattr(record, name)) in within
        return validator
    return length_validator
