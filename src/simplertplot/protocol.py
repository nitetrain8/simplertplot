"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition


"""
import contextlib
import queue
import threading

import numpy as np

from simplertplot import serializer
from simplertplot.eventloop import get_event_loop
from simplertplot.queues import RingBuffer
from simplertplot.transport import SocketTransport
from . import exceptions

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


class BadHandshake(exceptions.RTPlotException):
    pass


class BaseProtocol():
    OP_XY = 0
    OP_XYL = 1
    OP_XLYL = 2
    OP_EXIT = 3
    OP_NP_XYL = 4
    OP_NP_XLYL = 5
    transport_factory = SocketTransport
    _NP_DTYPE = float

    ST_STARTUP = 0
    ST_HANDSHAKE = 1
    ST_PUMP = 2

    def __init__(self, addr_or_sock, loop, serial_method=None):
        self.dlock = threading.Lock()
        self.transport = self.transport_factory(addr_or_sock)
        if loop is None:
            loop = get_event_loop()
        self.loop = loop
        self.serializer = serializer.get_serializer(serial_method)
        self._state = self.ST_STARTUP
        self.dtype = self._NP_DTYPE

    @contextlib.contextmanager
    def lock_queue(self):
        with self.dlock:
            yield

    def step_work(self):
        raise NotImplementedError

    def start(self):
        self.loop.add_worker(self.step_work)

    def stop(self):
        self.loop.remove_worker(self.step_work)


class UserSideProtocol(BaseProtocol):

    def __init__(self, client_socket, q, *, loop=None):
        """
        :param client_socket: address
        :type client_socket: (str, int)
        :param q: queue.Queue
        :type q: queue.Queue
        :param loop: event loop
        :type loop: event loop
        """

        super().__init__(client_socket, loop)
        self._queue = q

    def step_work(self):
        try:
            op, data = self._queue.get(False, None)
        except queue.Empty:
            return
        msg = self.serializer.dumps((op, data))
        self.transport.write(msg)

    def put_xy(self, x, y):
        self._queue.put((self.OP_XY, (x, y)))

    def put_xyl(self, xyl):
        """
        Put a list of (x, y) data into queue.
        note the race condition here- since lists are mutable,
        make a copy to ensure that data isn't modified before
        the producer thread has a chance to serialize it.
        """
        if isinstance(xyl, list):
            xyl = tuple(xyl)
        self._queue.put((self.OP_XYL, xyl))

    def put_xlyl(self, xl, yl):
        if isinstance(xl, list):
            xl = tuple(xl)
        if isinstance(yl, list):
            yl = tuple(yl)
        self._queue.put((self.OP_XLYL, xl, yl))

    def put_np_xyl(self, np_xyl):
        """
        :param np_xyl: np.ndarray
        :type np_xyl: np.ndarray
        """
        data = np_xyl.tobytes()
        self._queue.put((self.OP_NP_XYL, data))

    def put_np_xlyl(self, npxl, npyl):
        """
        :param np_xyl: np.ndarray
        :type np_xyl: np.ndarray
        """
        xd = np.asarray(npxl, self._NP_DTYPE).tobytes()
        yd = np.asarray(npyl, self._NP_DTYPE).tobytes()
        self._queue.put((self.OP_NP_XLYL, (xd, yd)))

    def handshake(self, max_pts, style):
        assert self._state == self.ST_STARTUP
        self._state = self.ST_HANDSHAKE
        data = self.serializer.dumps((max_pts, style, self.dtype))
        self.transport.write(data)
        ack = self.transport.readline()
        if ack != b"ACK YAY\n":
            raise BadHandshake(ack)


class ClientSideProtocol(BaseProtocol):
    transport_factory = SocketTransport

    def __init__(self, addr_or_sock, *, loop=None):
        """
        :param addr_or_sock: address for socket.socket()
        :type addr_or_sock: (str, int)
        :param xq: x data queue
        :type xq: RingBuffer
        :param yq: y data queue
        :type yq: RingBuffer
        """

        super().__init__(addr_or_sock, loop)
        self.dlock = threading.Lock()
        self.xq = None
        self.yq = None
        self.addr = addr_or_sock
        self.current_update = 0
        self.serializer = serializer.PickleSerializer()
        self.step_work = self.pump_data().__next__

    def step_work(self):
        pass  # skeleton, set in __init___

    def pump_data(self):
        put_x = self.xq.put
        ex_x = self.xq.extend
        put_y = self.yq.put
        ex_y = self.yq.extend
        lock = self.dlock
        tp = self.transport
        self.current_update = 0
        load_data = self.serializer.load

        while True:
            yield
            if not tp.have_data():
                continue
            try:
                code, data = load_data(tp)
            except EOFError:
                logger.debug("EOFError loading pickle: Connection Lost")
                tp.reconnect()
                continue
            if code == self.OP_XY:
                x, y = data
                with lock:
                    put_x(x)
                    put_y(y)
                self.current_update += 1
            elif code == self.OP_XYL:
                for x, y in data:
                    with lock:
                        put_x(x)
                        put_y(y)
                self.current_update += len(data)
            elif code == self.OP_XLYL:
                x_data, y_data = data
                with lock:
                    ex_x(x_data)
                    ex_y(y_data)
                self.current_update += len(x_data)
            elif code == self.OP_EXIT:
                break
            elif code == self.OP_NP_XLYL:
                xl, yl = data
                xl = np.frombuffer(xl, self._NP_DTYPE)
                yl = np.frombuffer(yl, self._NP_DTYPE)
                with lock:
                    ex_x(xl)
                    ex_y(yl)
                self.current_update += len(xl)
            else:
                logger.error("Invalid code: %d %s" % (code, data))
                raise ValueError(code)

    def handshake(self):
        from . import client_plotter
        max_pts, style, dtype = self.serializer.load(self.transport)
        # max_pts = 1000; style='ggplot'; dtype=float
        self.xq = RingBuffer(max_pts, dtype)
        self.yq = RingBuffer(max_pts, dtype)
        plot = client_plotter.RTPlotter(self, self.xq, self.yq, max_pts, style)
        self.transport.write(b"ACK YAY\n")
        return plot



