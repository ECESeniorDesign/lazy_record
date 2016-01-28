class RecordNotFound(Exception):
    pass


class RecordInvalid(Exception):
    pass


class QueryInvalid(Exception):
    pass


class AssociationTypeMismatch(Exception):
    pass

class MissingAttributeError(Exception):
    pass

class AssociationForbidden(Exception):
    pass
