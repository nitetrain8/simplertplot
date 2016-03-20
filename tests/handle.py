"""

Created by: Nathan Starkweather
Created on: 03/19/2016
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


import win32api, sys, os
import simplertplot
import win32process
import win32pipe


def quote(s):
    s = s.strip('"').strip("'")
    return '"%s"' % s

import msvcrt

def spawn_proc():
    si = win32process.STARTUPINFO()
    src = """
from simplertplot import start_client
import sys
start_client.start_client(sys.argv)"""
    python = sys.executable
    srp = os.path.dirname(simplertplot.__file__)
    cmd = "%s -c %s \"localhost\" 12345" % (quote(python), quote(src))
    import multiprocessing.spawn
    print(cmd)
    si.hStdInput = None
    null = None
    w, r = win32pipe.CreatePipe(None, 0)
    fdw = msvcrt.get_osfhandle(w)
    fdr = msvcrt.get_osfhandle(r)
    fw = os.fdopen(fdw, 'w')
    fr = os.fdopen(fdr, 'r')


    # win32process.CreateProcess()

if __name__ == '__main__':
    spawn_proc()
