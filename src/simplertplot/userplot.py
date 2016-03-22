"""

Created by: Nathan Starkweather
Created on: 03/21/2016
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


_spawn_src = """
from simplertplot import start_client
import sys
start_client.start_client(sys.argv)"""


class RTPlot():
    def __init__(self, max_pts=1000, style='ggplot', con_type='tcp'):
        self.max_pts = max_pts
        self.style = style
        self.con_type = con_type
        self.protocol = None
        self.queue = None

    def show(self):
        assert self.con_type == 'tcp'
        from . import manager
        m = manager.get_manager()
        self.protocol, self.queue = m.new_user_plot(self, self.max_pts)
        self.protocol.handshake(self.max_pts, self.style)
        self.protocol.start()

    def put_xy(self, x, y):
        self.protocol.put_xy(x, y)

    def put_xyl(self, xyl):
        self.protocol.put_xyl(xyl)

    def put_xlyl(self, xl, yl):
        self.protocol.put_xlyl(xl, yl)

    def put_np_xyl(self, np_xyl):
        self.protocol.put_np_xlyl(np_xyl)

    def put_np_xlyl(self, npxl, npyl):
        self.protocol.put_np_xlyl(npxl, npyl)



