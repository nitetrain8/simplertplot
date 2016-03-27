"""

Created by: Nathan Starkweather
Created on: 03/21/2016
Created in: PyCharm Community Edition


"""

__author__ = 'Nathan Starkweather'

import logging

from simplertplot import protocols
from simplertplot import transport
import queue
import simplertplot

logger = logging.getLogger(__name__)
_h = logging.StreamHandler()
_f = logging.Formatter("%(created)s %(name)s %(levelname)s (%(lineno)s): %(message)s")
_h.setFormatter(_f)
logger.addHandler(_h)
logger.propagate = False
logger.setLevel(logging.DEBUG)
del _h, _f


class RTPlot():
    plot_type = "xyplotter"
    _DEFAULT_HOST = 'localhost'
    _DEFAULT_PORT = 18043

    def __init__(self, max_pts=10000, style='ggplot', con_type='tcp'):
        self.max_pts = max_pts
        self.style = style
        self.con_type = con_type
        self.producer = None
        self.queue = queue.Queue(max_pts)

    def show(self):
        proto_factory = lambda: protocols.XYUserProtocol(self.queue)

        self.manager = simplertplot.manager.get_user_manager()
        self.producer = self.manager.spawn_standalone((self._DEFAULT_HOST, self._DEFAULT_PORT), self.plot_type,
                                                      self.style, self.max_pts,
                                                      self.con_type, proto_factory)
        self.manager.run_protocol(self.producer)

    def destroy(self):
        """ Destroy the plot, freeing all references """
        self.manager.stop_protocol(self.producer)
        while self.__dict__:
            self.__dict__.popitem()

    def test_rpc(self, msg):
        return self.producer.put_rpc("test_rpc", msg)

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
    plot_type = "echo"

    def __init__(self):
        pass

    def show(self):
        host = 'localhost'
        port = 0
        self.server = transport.TCPServer(host, port)
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



