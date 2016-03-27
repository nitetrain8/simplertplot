"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition


"""
import contextlib
import pickle
import queue
import threading
import time
from concurrent.futures import Future

import numpy as np
from simplertplot.queues import RingBuffer

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


class RPCRequest():
    def __init__(self, func, args, kwargs):
        self.kwargs = kwargs
        self.args = args
        self.func = func
        self.id = id(self)

    def respond(self, value=None, exc=None):
        fut = RPCResponse(self.id, value, exc)
        return fut


class RPCResponse():
    notset = object

    def __init__(self, id=None, value=notset, exc=notset):
        self.id = id
        self.value = value
        self.exc = exc


class BaseProtocol():
    OP_XY = 0
    OP_XYL = 1
    OP_XLYL = 2
    OP_EXIT = 3
    OP_NP_XYL = 4
    OP_NP_XLYL = 5
    OP_RPC = 6
    _NP_DTYPE = np.float64

    def __init__(self, serial_method='pickle'):
        self.dlock = threading.Lock()
        self.transport = None
        if serial_method == 'pickle':
            self.deserialize = pickle.load
            self.serialize = pickle.dumps
        else:
            raise ValueError(serial_method)
        self._pending_futures = {}

    def connection_made(self, transport):
        self.transport = transport

    @contextlib.contextmanager
    def lock_queue(self):
        with self.dlock:
            yield

    def step_work(self):
        raise NotImplementedError


class XYUserProtocol(BaseProtocol):

    def __init__(self, q):
        """
        :param q: queue.Queue
        :type q: queue.Queue
        """

        super().__init__()
        self._queue = q
        self.step_work = self._step_work().__next__

    def _step_work(self):
        while self.transport is None:
            yield
        while True:
            r, w, x = self.transport.select()
            if w:
                try:
                    op, data = self._queue.get(False, None)
                except queue.Empty:
                    pass
                else:
                    msg = self.serialize((op, data))
                    self.transport.write(msg)
            if r:
                op, data = self.deserialize(self.transport)
                if op == self.OP_RPC:
                    rsp = data
                    fut = self._pending_futures.pop(rsp.id)
                    if rsp.exc:
                        fut.set_exception(rsp.exc)
                    else:
                        fut.set_result(rsp.value)
                else:
                    logger.error("Unsupported op: %d", op)
            yield

    def step_work(self):
        pass

    def put_rpc(self, func_name, *args, **kwargs):
        req = RPCRequest(func_name, args, kwargs)
        fut = Future()
        self._queue.put((self.OP_RPC, req))
        self._pending_futures[req.id] = fut
        return fut

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
        :param npxl: np.ndarray
        :type npyl: np.ndarray
        """
        xd = np.asarray(npxl, self._NP_DTYPE).tobytes()
        yd = np.asarray(npyl, self._NP_DTYPE).tobytes()
        self._queue.put((self.OP_NP_XLYL, (xd, yd)))


class XYPlotterProtocol(BaseProtocol):

    def __init__(self, xq, yq, rpc_req, rpc_rsp):
        """
        :param xq: x data queue
        :type xq: RingBuffer
        :param yq: y data queue
        :type yq: RingBuffer
        """

        super().__init__()
        self.rpc_req = rpc_req
        self.rpc_rsp = rpc_rsp
        self.dlock = threading.Lock()
        self.xq = xq
        self.yq = yq
        self.current_update = 0
        self.step_work = self.pump_data().__next__

    def step_work(self):
        pass  # set in __init___

    def pump_data(self):
        put_x = self.xq.put
        ex_x = self.xq.extend
        put_y = self.yq.put
        ex_y = self.yq.extend
        lock = self.dlock
        tp = self.transport
        self.current_update = 0
        deserialize = self.deserialize
        serialize = self.serialize

        while True:
            yield
            r, w, _ = tp.select()
            if r:
                try:
                    code, data = deserialize(tp)
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
                elif code == self.OP_RPC:
                    self.rpc_req.put(data)
                else:
                    raise ValueError(code)

            if w:
                try:
                    rsp = self.rpc_rsp.get(False)
                except queue.Empty:
                    pass
                else:
                    msg = serialize((self.OP_RPC, rsp))
                    tp.write(msg)


