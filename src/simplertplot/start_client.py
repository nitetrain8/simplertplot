"""

Created by: Nathan Starkweather
Created on: 03/19/2016
Created in: PyCharm Community Edition


"""
import os

from simplertplot.client_plotter import RTPlotter
from simplertplot.workers import ClientProtocol
from simplertplot.queues import RingBuffer

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


def start_client(argv):
    host = argv[1]
    port = int(argv[2])
    addr = (host, port)
    plotter = RTPlotter(addr, 100000, 'ggplot')
    plotter.run_forever()


if __name__ == '__main__':
    start_client()
