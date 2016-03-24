"""

Created by: Nathan Starkweather
Created on: 03/19/2016
Created in: PyCharm Community Edition


"""
import os

import argparse
from simplertplot.plots import get_plot_class

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


def parse_cmd_line(args):
    p = argparse.ArgumentParser(description="Launch Real-Time Matplotlib Plot Server")
    p.add_argument("host", type=str.lower)
    p.add_argument("port", type=int)
    p.add_argument("--plot", default="XYPlotter", type=str.lower)
    p.add_argument("--mproto", default="tcp", help="Message protocol", choices=("tcp",), type=str.lower)
    rv = p.parse_args(args)
    return rv


def start_client(ns):
    host = ns.host
    port = ns.port
    plot = ns.plot
    addr = (host, port)
    plt_kls = get_plot_class(plot)
    plotter = plt_kls(addr, 10000, 'ggplot')
    plotter.run_forever()


def proc_server_startup_main():
    import sys
    ns = parse_cmd_line(sys.argv[1:])
    start_client(ns)
