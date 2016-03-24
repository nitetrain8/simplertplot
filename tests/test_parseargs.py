"""

Created by: Nathan Starkweather
Created on: 03/23/2016
Created in: PyCharm Community Edition

Module: test_module
Functions: test_functions

"""
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


from simplertplot.start_client import parse_cmd_line


def test_parseargs1():
    host = 'localhost'
    port = 12345
    cmd_line = "-c %s %d" % (host, port)
    argv = cmd_line.split()
    ns = parse_cmd_line(argv[1:])
    assert ns.host == host
    assert ns.port == port
    assert ns.plot == "XYPlotter"
    assert ns.mproto == "tcp"


def test_parseargs2():
    pytest.raises(SystemExit, parse_cmd_line, [])

def test_parseargs3():
    args = ['LOCALHOST', '12345', '--plot=XYPloTter', '--mproto=TCP']
    ns = parse_cmd_line(args)
    assert ns.host == 'localhost'
    assert ns.port == 12345
    assert ns.plot == "xyplotter"
    assert ns.mproto == "tcp"

if __name__ == '__main__':
    pytest.main()
