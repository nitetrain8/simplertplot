"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition

Module: test_module
Functions: test_functions

"""
import pickle
import pytest
from os import makedirs
import sys
# noinspection PyUnresolvedReferences
from os.path import dirname, join, exists, basename
from shutil import rmtree
import logging

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


def setup_module():
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


def teardown_module():
    try:
        rmtree(temp_dir)
    except FileNotFoundError:
        pass

    for p in (curdir, local_test_input):
        try:
            sys.path.remove(p)
        except Exception:
            pass


if __name__ == '__main__':
    pytest.main()

import threading
import socket
from simplertplot import transport


def blocking(addr, nmessages, flag):
    t = transport.SocketTransport(addr)
    for _ in range(nmessages):
        try:
            pickle.load(t)
        except pickle.PickleError:
            flag.set()
            return


import time

def test_transport_blocking():
    """
    This test needs to make sure that loading
    a pickled TCP message using a buffered reader
    returned by socket.makefile() blocks correctly
    while waiting for the message to be sent.
    """
    s = socket.socket()
    s.bind(('localhost', 0))
    s.listen(1)

    addr = s.getsockname()
    nmessages = 3
    fail = threading.Event()

    bt = threading.Thread(None, blocking, None, (addr, nmessages, fail), daemon=True)
    bt.start()
    w, _ = s.accept()
    message = pickle.dumps(list(range(20)))
    first, second = message[:10], message[10:]
    assert first + second == message
    for _ in range(nmessages):
        w.send(first)
        time.sleep(0.1)  # force thread switch
        w.send(second)
    assert not fail.is_set()
