from lazy_record.errors import *


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
            if not validation(getattr(self, attr)):
                reason[attr] = getattr(self, attr)
                valid = False
        if not valid:
            raise RecordInvalid(reason)
