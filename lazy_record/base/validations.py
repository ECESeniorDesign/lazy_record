from lazy_record.errors import *
import lazy_record.validations as validators

class Validations(object):
    __validates__ = {}

    def validate(self):
        """
        Validate an object against the __validates__ class variable.
        Returns None on success, and raises RecordInvalid if validations fail.
        """
        reason = {}
        valid = True
        for attr, validation in self.__class__.__validates__.items():
            if validation.__module__ == 'lazy_record.validations':
                if validation.__name__ != "validator":
                    # Close them around the attr name
                    self.__class__.__validates__[attr] = validation(attr)
            if not validation(self):
                reason[attr] = getattr(self, attr)
                valid = False
        if not valid:
            raise RecordInvalid(reason)
