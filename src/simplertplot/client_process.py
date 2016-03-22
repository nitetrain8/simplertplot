"""

Created by: Nathan Starkweather
Created on: 03/19/2016
Created in: PyCharm Community Edition


"""
import os

from simplertplot.client_plotter import RTPlotter
from simplertplot import manager

__author__ = 'Nathan Starkweather'

import logging

logger = logging.getLogger(__name__)
_h = logging.StreamHandler()
_f = logging.Formatter("%(created)s %(name)s %(levelname)s (%(lineno)s): %(message)s")
_h.setFormatter(_f)
logger.addHandler(_h)
pth = os.path.join("C:/.replcache/", os.path.basename(__file__).replace(".py", ".log"))
_h2 = logging.FileHandler(pth, 'w')
_h2.setFormatter(_f)
logger.propagate = False
logger.setLevel(logging.DEBUG)
del _h, _f, _h2


def startup_client(args):
    if args[0] == '-c' or os.path.exists(args[0]):
        args = args[1:]
    host = args[0]
    port = int(args[1])
    addr = (host, port)
    m = manager.create_client_manager(addr)
    m.event_loop.run


if __name__ == '__main__':
    import sys
    startup_client(sys.argv[1:])
