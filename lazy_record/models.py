from inflector import Inflector, English
from lazy_record.errors import *

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
    return fk in model._attributes()

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
