"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition


"""
import contextlib
import pickle
import threading

from simplertplot.eventloop import get_event_loop
from simplertplot.queues import RingBuffer
from simplertplot.transport import SocketTransport

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


class BaseProtocol():
    OP_XY = 0
    OP_XYL = 1
    OP_XLYL = 2
    OP_EXIT = 3
    transport_factory = SocketTransport

    def __init__(self, addr, *, loop=None):
        self.dlock = threading.Lock()
        self.transport = self.transport_factory(addr)
        if loop is None:
            loop = get_event_loop()
        self.loop = loop

    @contextlib.contextmanager
    def lock_queue(self):
        with self.dlock:
            yield

    def step_work(self):
        raise NotImplementedError


class ServerProtocol(BaseProtocol):
    def __init__(self, addr, q):
        super().__init__(addr)
        self.queue = q


class ClientProtocol(BaseProtocol):
    transport_factory = SocketTransport

    def __init__(self, addr, xq, yq):
        """
        :param addr: address for socket.socket()
        :type addr: (str, int)
        :param xq: x data queue
        :type xq: RingBuffer
        :param yq: y data queue
        :type yq: RingBuffer
        """

        super().__init__(addr)
        self.dlock = threading.Lock()
        self.xq = xq
        self.yq = yq
        self.addr = addr
        self.thread = None
        self.deserializer = pickle.load
        self.current_update = 0
        self.step_work = self.pump_data().__next__

    def start(self):
        self.loop.add_worker(self)

    def stop(self):
        self.loop.remove_worker(self)

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
        deserializer = self.deserializer

        while True:
            yield
            try:
                code, data = deserializer(tp)
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
                        put_x(x); put_y(y)
                self.current_update += len(data)
            elif code == self.OP_XLYL:
                x_data, y_data = data
                with lock:
                    ex_x(x_data)
                    ex_y(y_data)
                self.current_update += len(x_data)
            elif code == self.OP_EXIT:
                break
            else:
                raise ValueError(code)
