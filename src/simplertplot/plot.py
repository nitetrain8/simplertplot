"""

Created by: Nathan Starkweather
Created on: 03/21/2016
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

import logging
import sys
import subprocess
from simplertplot import util
from simplertplot import workers
from simplertplot import transport
import queue

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
        self.producer = None
        self.queue = queue.Queue(max_pts)
        self.popen = None

    def show(self):
        assert self.con_type == 'tcp'
        python = sys.executable
        host = 'localhost'
        s = transport.SimpleServer(host)
        host, port = s.get_addr()
        cmd = "%s -c %s %s %d" % (util.quote(python), util.quote(_spawn_src), host, port)
        self.popen = subprocess.Popen(cmd)
        client = s.accept_connection(True)
        self.producer = workers.UserSideProtocol(client, self.queue)
        self.producer.start()

    def put_xy(self, x, y):
        self.producer.put_xy(x, y)

    def put_xyl(self, xyl):
        self.producer.put_xyl(xyl)

    def put_xlyl(self, xl, yl):
        self.producer.put_xlyl(xl, yl)

    def put_np_xyl(self, np_xyl):
        self.producer.put_np_xlyl(np_xyl)

    def put_np_xlyl(self, npxl, npyl):
        self.producer.put_np_xlyl(npxl, npyl)



