"""

Created by: Nathan Starkweather
Created on: 03/21/2016
Created in: PyCharm Community Edition


"""
import pickle

__author__ = 'Nathan Starkweather'

import logging

logger = logging.getLogger(__name__)
_h = logging.StreamHandler()
_f = logging.Formatter("%(created)s %(name)s %(levelname)s (%(lineno)s): %(message)s")
_h.setFormatter(_f)
logger.addHandler(_h)
logger.propagate = False
logger.setLevel(logging.DEBUG)
del _h, _f


class PickleSerializer():
    def __init__(self):
        pass

    def dumps(self, data):
        return pickle.dumps(data)

    def dump(self, data, file):
        return pickle.dump(data, file)

    def load(self, file):
        return pickle.load(file)

    def loads(self, s):
        return pickle.loads(s)


def get_serializer(method):
    if method is None:
        return PickleSerializer()
    elif method.lower() == 'pickle':
        return PickleSerializer()
    else:
        raise ValueError(method)
