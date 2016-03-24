"""

Created by: Nathan Starkweather
Created on: 03/19/2016
Created in: PyCharm Community Edition

Module: test_module
Functions: test_functions

"""
import queue
import socket
import sys
import threading
import unittest
from os import makedirs
import subprocess, sys
# noinspection PyUnresolvedReferences
from os.path import dirname, join, exists, basename
from shutil import rmtree
import logging

import numpy as np

import simplertplot
import pickle

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


def quote(s):
    s = s.strip('"').strip("'")
    return '"%s"' % s


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

from simplertplot import userplot

class TestStartclient(unittest.TestCase):
#     @unittest.skip
#     def test_start_client(self):
#         """
#         @return: None
#         @rtype: None
#         """
#
#         src = """
# from simplertplot import start_client
# import sys
# start_client.start_client(sys.argv)"""
#         python = sys.executable
#         host = 'localhost'
#         port = 12345
#         cmd = "%s -c %s \"%s\" %d" % (quote(python), quote(src), host, port)
#         p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
#         spawn_sin_producer((host, port))
#         p.wait()

    def test_start_client2(self):
        """
        @return: None
        @rtype: None
        """

        plot = userplot.RTPlot()
        plot.show()
        spawn_sin_producer2(plot)
        plot.popen.wait()

    def test_start_client3(self):
        plot = userplot._UserEchoPlot()
        plot.show()

        def check_ping(msg):
            __tracebackhide__ = True
            r, s = plot.ping(msg)
            assert r == s

        check_ping("Hello WOrld")
        check_ping("Bye World")
        check_ping("foobarbaz")
        plot.stop()



def spawn_sin_producer(addr):
    server = socket.socket()
    server.bind(addr)
    server.listen(1)
    # server.settimeout(5)
    sock, addr = server.accept()
    step = 0.0005
    dt = 0.0005
    thread = threading.Thread(None, sin_producer2, "ProdThread", (sock, step, dt), daemon=True)
    thread.start()


def spawn_sin_producer2(plot):
    step = 0.0005
    dt = 0.0005
    thread = threading.Thread(None, sin_producer4, "ProdThread", (plot, step, dt), daemon=True)
    thread.start()


import math
import time


def sin_producer(sock, step=0.05, dt=0.05):
    OP_XY = 0
    OP_XYL = 1
    OP_XLYL = 2
    OP_EXIT = 3
    x = 0
    while True:
        y = math.sin(x)
        data = (OP_XY, (x, y))
        s = pickle.dumps(data)
        import io
        b = io.BytesIO()
        pickle.load(b)
        sock.sendall(s)
        x += step
        time.sleep(dt)


def sin_producer2(sock, step=0.05, dt=0.01):
    OP_XY = 0
    OP_XYL = 1
    OP_XLYL = 2
    OP_EXIT = 3
    x = 0
    buf = []
    i = 1
    q = queue.Queue()
    prod = simplertplot.workers.UserClientProtocol(sock, q)
    prod.start()
    while True:
        y = math.sin(x)
        buf.append((x, y))
        x += step
        if not (i % 1):
            i = 0
            prod.put_xyl(buf)
            buf.clear()
        time.sleep(dt)
        i += 1


def sin_producer3(sock, step=0.05, dt=0.01):
    OP_XY = 0
    OP_XYL = 1
    OP_XLYL = 2
    OP_EXIT = 3
    x = 0
    buf = []
    i = 1
    q = queue.Queue()
    prod = simplertplot.workers.UserClientProtocol(sock, q)
    prod.start()
    while True:
        y = math.sin(x)
        buf.append((x, y))
        x += step
        if not (i % 1):
            i = 0
            xdata, ydata = tuple(zip(*buf))
            npx = np.asarray(xdata)
            npy = np.asarray(ydata)
            prod.put_np_xlyl(npx, npy)
            buf.clear()
        end = time.time() + dt
        while time.time() < end:
            pass
        # time.sleep(dt)

        i += 1


def sin_producer4(plot, step=0.05, dt=0.01):
    OP_XY = 0
    OP_XYL = 1
    OP_XLYL = 2
    OP_EXIT = 3
    x = 0
    buf = []
    i = 1
    while True:
        y = math.sin(x)
        buf.append((x, y))
        x += step
        if not (i % 10):
            i = 0
            plot.put_xyl(buf)
            buf.clear()
        time.sleep(dt)
        i += 1


if __name__ == '__main__':
    unittest.main()
