"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition

Module: test_module
Functions: test_functions

"""
import unittest, pytest
from collections import deque
from os import makedirs
import sys
# noinspection PyUnresolvedReferences
from os.path import dirname, join, exists, basename
from shutil import rmtree
import logging

import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
_h = logging.StreamHandler()
_f = logging.Formatter("%(created)s %(name)s %(levelname)s (%(lineno)s): %(message)s")
_h.setFormatter(_f)
logger.addHandler(_h)
logger.propagate = False
del _h, _f

__author__ = 'Administrator'

curdir = dirname(__file__)
test_dir = dirname(curdir)
test_temp_dir = join(test_dir, "temp")
temp_dir = join(test_temp_dir, "temp_dir_path")
test_input = join(curdir, "test_input")
local_test_input = join(test_input, basename(__file__.replace(".py", "_input")))


def setUpModule():
    for d in temp_dir, test_input, local_test_input:
        try:
            makedirs(d)
        except FileExistsError:
            pass
    set_up_pyfile_logger()
    sys.path.append(curdir)
    sys.path.append(local_test_input)


def set_up_pyfile_logger():
    global pyfile_logger
    pyfile_logger = logging.getLogger("pyfile_" + basename(__file__.replace(".py", "")))
    pyfile_formatter = logging.Formatter("")
    pyfile_handler = logging.FileHandler(join(test_input, local_test_input, "dbg_ut.py"), 'w')
    pyfile_logger.addHandler(pyfile_handler)
    pyfile_handler.setFormatter(pyfile_formatter)


def tearDownModule():
    try:
        rmtree(temp_dir)
    except FileNotFoundError:
        pass

    for p in (curdir, local_test_input):
        try:
            sys.path.remove(p)
        except Exception:
            pass


import itertools
from simplertplot import queues


class TestRingBuffer(unittest.TestCase):
    def test_rb_basic(self):
        rb = queues.RingBuffer(3, int)
        l0 = [0, 0, 0]
        l1 = [1, 0, 0]
        l2 = [1, 2, 0]
        l3 = [1, 2, 3]
        l4 = [4, 2, 3]
        l5 = [4, 5, 3]
        l6 = [4, 5, 6]
        it = itertools.count(1).__next__
        for l in (l0, l1, l2, l3, l4, l5, l6):
            exp = l
            res = rb._queue.tolist()
            self.assertEqual(exp, res)
            v = it()
            rb.put(v)

    def test_rb_get(self):
        rb = queues.RingBuffer(3, int)
        exp = [
            [1],
            [1, 2],
            [1, 2, 3],
            [2, 3, 4],
            [3, 4, 5],
            [4, 5, 6],
            [5, 6, 7],
            [6, 7, 8]
        ]
        it = itertools.count(1).__next__
        for e in exp:
            v = it()
            rb.put(v)
            res = rb.get().tolist()
            self.assertEqual(e, res)

    def test_set_slice(self):
        rb = queues.RingBuffer(3, int)
        it = itertools.count(1).__next__
        for _ in range(3):
            rb.put(it())

        assert rb._queue.tolist() == [1, 2, 3]
        assert rb.get().tolist() == [1, 2, 3]
        rb.put_list([4, 5])
        assert rb.get().tolist() == [3, 4, 5]
        rb.put_list([1, 2])
        assert rb.get().tolist() == [5, 1, 2]
        rb.put_list([3, 4])
        assert rb.get().tolist() == [2, 3, 4]
        rb.put(5)
        assert rb.get().tolist() == [3, 4, 5]
        rb.put_list([6, 7])
        assert rb.get().tolist() == [5, 6, 7]

    def test_set_slice2(self):
        rb = queues.RingBuffer(3, int)
        rb.put_list([1, 2])
        assert rb.get().tolist() == [1, 2]
        rb.put(3)
        assert rb.get().tolist() == [1, 2, 3]

    def test_set_slice3(self):
        rb = queues.RingBuffer(3, int)
        rb.put(1)
        rb.put_list([2, 3])
        assert rb.get().tolist() == [1, 2, 3]
        rb.put(4)
        assert rb.get().tolist() == [2, 3, 4]

    def test_set_slice4(self):
        rb = queues.RingBuffer(3, int)
        rb.put(1)
        rb.put(2)
        rb.put_list([3, 4])
        assert rb.get().tolist() == [2, 3, 4]

    def test_set_slice_err(self):
        rb = queues.RingBuffer(3, int)
        self.assertRaises(ValueError, rb.put_list, ([1, 2, 3, 4]))

    def test_set_slice5(self):
        rb = queues.RingBuffer(3, int)
        rb.put_list([1, 2, 3])
        assert rb.get().tolist() == [1, 2, 3]
        rb.put(4)
        assert rb.get().tolist() == [2, 3, 4]


def generator(slc):
    for item in slc:
        yield item


@pytest.mark.parametrize('conv', [tuple, list, np.asarray, generator])
@pytest.mark.parametrize('nstart', list(range(6)))
@pytest.mark.parametrize('slen', list(range(6)))
@pytest.mark.parametrize('nputs', list(range(6)))
def test_set_slice6(nstart, slen, nputs, conv):
    count = itertools.count(1)
    nc = count.__next__
    new = new_deque_ringbuffer
    put = put_item
    extend = extend_items
    get_slc = get_slice

    def verify():
        __tracebackhide__ = True
        nonlocal d, rb
        verify_equal(d, rb)

    init = [nc() for _ in range(nstart)]
    v = nc()
    slc = get_slc(nc, slen)

    # put, then slice
    d, rb = new(5, init)
    for _ in range(nputs):
        put(d, v)
        put(rb, v)
    extend(d, conv(slc))
    extend(rb, conv(slc))
    verify()

    # slice, then put
    d, rb = new(5, init)
    extend(d, conv(slc))
    extend(rb, conv(slc))
    put(d, v)
    put(rb, v)
    verify()


def new_deque_ringbuffer(len=5, initializer=()):
    d = deque(maxlen=len)
    rb = queues.RingBuffer(len, int)
    for v in initializer:
        put_item(d, v)
        put_item(rb, v)
    return d, rb


def put_item(q, item):
    if isinstance(q, queues.RingBuffer):
        q.put(item)
    elif isinstance(q, deque):
        q.append(item)
    else:
        q.append(item)


def extend_items(q, items):
    if isinstance(q, queues.RingBuffer):
        q.extend(items)
    elif isinstance(q, deque):
        for i in items:
            q.append(i)
    else:
        q.extend_items(items)


def get_as_list(q):
    if isinstance(q, queues.RingBuffer):
        return q.get().tolist()
    else:
        return list(q)


def get_slice(nc, slen):
    slc = []
    for i in range(slen):
        slc.append(nc())
    return slc


def verify_equal(d, rb, msg=None):
    __tracebackhide__ = True
    equal = get_as_list(d) == get_as_list(rb)
    assert equal, msg if msg else ""


if __name__ == '__main__':
    unittest.main()
