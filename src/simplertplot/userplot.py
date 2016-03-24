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
start_client.proc_server_startup_main()
"""


def _spawn_process(host, port, plot):
    python = sys.executable
    cmd = "%s -c %s %s %d --plot=%s" % (util.quote(python), util.quote(_spawn_src), host, port, plot)
    return subprocess.Popen(cmd)


class RTPlot():
    _plot_type_ = "xyplotter"

    def __init__(self, max_pts=1000, style='ggplot', con_type='tcp'):
        self.max_pts = max_pts
        self.style = style
        self.con_type = con_type
        self.producer = None
        self.queue = queue.Queue(max_pts)
        self.popen = None

    def show(self):
        assert self.con_type == 'tcp'
        host = 'localhost'
        s = transport.SimpleServer(host)
        host, port = s.get_addr()
        self.popen = _spawn_process(host, port, self._plot_type_)
        client = s.accept_connection(True)
        self.producer = workers.UserClientProtocol(client, self.queue)
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


class _UserEchoPlot():
    def __init__(self):
        pass

    def show(self):
        host = 'localhost'
        port = 0
        self.server = transport.SimpleServer(host, port)
        host, port = self.server.get_addr()
        self.popen = _spawn_process(host, port, "echo")
        self.client_sock = self.server.accept_connection()
        self.writer = self.client_sock.makefile('wb')
        self.reader = self.client_sock.makefile('rb')

    def ping(self, msg):
        sent = self.send_msg(msg)
        received = self.reader.read(len(sent))
        return sent, received

    def send_msg(self, msg):
        if not isinstance(msg, bytes):
            sent = bytes(msg, 'ascii')
        else:
            sent = msg
        if len(sent) > 999:
            raise ValueError("Max ping size: 999 bytes")
        self.writer.write(("%03d" % len(sent)).encode('ascii'))
        self.writer.write(sent)
        self.writer.flush()
        logger.debug("SENT: %s", sent)
        return sent

    def stop(self):
        self.send_msg(b'SYS_EXIT')
        self.popen.wait(5)



