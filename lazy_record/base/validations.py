from lazy_record.errors import *
import lazy_record.validations as validators

class Validations(object):
    __validates__ = {}

    def is_valid(self, attrs = None):
        """
        Validate an object against the __validates__ class variable.
        Returns True if valid, and False if any validations fail. If passed
        (as a dict), +attrs+ will be populated with the invalid attributes.
        """
        if attrs is None:
            reason = {}
        else:
            reason = attrs
        valid = True
        for attr, validation in self.__class__.__validates__.items():
            if validation.__class__ == validators.validation:
                validation.name = attr
            if not validation(self):
                reason[attr] = getattr(self, attr)
                valid = False
        return valid

    def validate(self):
        """
        Validate an object against the __validates__ class variable.
        Returns None on success, and raises RecordInvalid if validations fail.
        """
        reason = {}
        if not self.is_valid(attrs=reason):
            raise RecordInvalid(reason)
