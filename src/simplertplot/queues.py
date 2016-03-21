"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition


"""
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


import numpy as np


class RingBuffer():
    """ Numpy-based ring buffer """
    _default_dtype = np.float32

    def __init__(self, maxsize, dtype=_default_dtype):
        if not maxsize or maxsize < 0:
            raise ValueError("%s requires max size argument" % self.__class__.__name__)
        self._queue = np.zeros(maxsize, dtype)
        self._dtype = dtype
        self._maxsize = maxsize
        self._end = 0
        self._sz = 0

    def put(self, d):
        self._queue[self._end] = d
        self._end += 1
        if self._end == self._maxsize:
            self._end = 0
        if self._sz < self._maxsize:
            self._sz += 1

    def put_list(self, lst):
        """
        :param lst: list to extend data from
        :type lst: list | tuple | np.ndarray
        """
        slen = len(lst)
        if slen > self._maxsize:
            raise ValueError("Can't add more than maxsize elements (%d > %d)" % (slen, self._maxsize))
        if slen + self._end <= self._maxsize:
            start = self._end
            end = slen + self._end
            self._queue[start:end] = lst
            self._end = end
        else:
            # add slice in two steps
            first_step = self._maxsize - self._end
            self._queue[self._end: self._maxsize] = lst[:first_step]
            second_step = slen - first_step
            self._queue[:second_step] = lst[first_step:]
            self._end = second_step

        if self._sz < self._maxsize:
            self._sz += slen
        if self._end == self._maxsize:
            self._end = 0

    def extend(self, it):
        try:
            it.__len__
        except AttributeError:
            if not isinstance(it, np.ndarray):
                it = tuple(it)
        self.put_list(it)

    def get(self):
        """
        Get method. Returns the entire queue but does NOT
        drain the queue.
        """
        if self._sz < self._maxsize:
            return self._queue[: self._end]
        else:
            return np.roll(self._queue, -self._end)

    def __len__(self):
        return self._sz
