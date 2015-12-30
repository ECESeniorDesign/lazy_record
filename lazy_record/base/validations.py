from errors import *

class Validations(object):
    __validates__ = {}
    def validate(self):
        reason = {}
        valid = True
        for attr, validation in self.__class__.__validates__.items():
            if not validation(getattr(self, attr)):
                reason[attr] = getattr(self, attr)
                valid = False
        if not valid:
            raise RecordInvalid(reason)
