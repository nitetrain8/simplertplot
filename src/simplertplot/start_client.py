"""

Created by: Nathan Starkweather
Created on: 03/19/2016
Created in: PyCharm Community Edition


"""
import socket
import threading

import pickle, os
import matplotlib.pyplot

__author__ = 'Nathan Starkweather'

import logging
import time
from matplotlib import pyplot
import tkinter as tk

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

import numpy as np


class RingBuffer():
    """ Numpy-based ring buffer """
    _default_dtype = [np.float32, np.float32]

    def __init__(self, maxsize, dtype=_default_dtype):
        if not maxsize or maxsize < 0:
            raise ValueError("%s requires max size to satisfy numpy impl" % self.__class__.__name__)
        self._queue = np.zeros(maxsize, dtype)
        self._maxsize = maxsize
        self._end = 0
        self._sz = 0

    def put(self, d):
        self._queue[self._end] = d
        self._end += 1
        if self._end == self._maxsize:
            self._end = 0
        if self._sz < self._maxsize:
            self._sz += 1

    def get(self):
        """
        Get method. Returns the entire queue but does NOT
        drain the queue.
        """
        if self._sz < self._maxsize:
            return self._queue[: self._end]
        else:
            return np.roll(self._queue, -self._end)

    def __len__(self):
        return len(self._queue)


class RTPlotter():
    """ Actual plotter process, running in spawned thread
    :ivar client: consumer protocol
    :type client: worker.ConsumerClientWorker
    """
    def __init__(self, addr, max_pts, style):
        assert max_pts > 0, "max_pts < 0: %s" % max_pts
        self.x_queue = RingBuffer(max_pts, float)
        self.y_queue = RingBuffer(max_pts, float)
        self.x_data = []
        self.y_data = []
        self.max_pts = max_pts
        self.style = style
        self.figure = None
        self.subplot = None
        self.fps_text = None
        self.npts_text = None
        self.debug_text = None
        self.debug_lines = ["", "", ""]
        self.data_lock = threading.Lock()
        self.client = Client(addr, self.x_queue, self.y_queue, self.data_lock)

    def clear_pyplot(self):
        if self.figure:
            pyplot.close(self.figure)
        self.figure = None
        self.subplot = None
        self.fps_text = None
        self.npts_text = None
        self.debug_text = None

    def setup_pyplot(self):
        """ Plot setup boilerplate """
        pyplot.style.use(self.style)

        self.figure = self.create_figure()
        self.subplot = self.figure.add_subplot(1, 1, 1)
        self.debug_text = self.subplot.text(0.01, 0.95, "", transform=self.subplot.transAxes,
                                            multialignment='left', va='top')

    def create_figure(self):
        # listed here in case they needed to get changed
        num = None
        figsize = None
        dpi = None
        facecolor = None
        edgecolor = None
        frameon = True
        figure = pyplot.figure(num, figsize, dpi, facecolor, edgecolor, frameon)
        return figure

    def run_forever(self):
        self.setup_pyplot()
        self.start_client()
        try:
            self.run_plot()
        except tk.TclError:  # often throws on shutdown
            pass

    def start_client(self):
        self.client.start()

    def run_plot(self):

        figure = self.figure
        figure.show()
        figure.draw(figure.canvas.renderer)

        frames = 0
        update_data = self.update_data

        subplot = self.subplot
        line, = subplot.plot(self.x_data, self.y_data)
        background = figure.canvas.copy_from_bbox(subplot.bbox)
        debug_text = self.debug_text
        debug_lines = self.debug_lines

        blit = self.figure.canvas.blit
        subplot_bbox = self.subplot.bbox
        flush_events = figure.canvas.flush_events

        _len = len
        _time = time.time
        start = _time()

        # avoid ZeroDivisionError on floating point arithmetic for fps calc
        while not (_time() - start):
            pass

        # mainloop
        while True:
            fps = frames / (_time() - start)
            debug_lines[0] = ("FPS:%.1f" % fps)
            dbg_txt = '\n'.join(debug_lines)
            debug_text.set_text(dbg_txt)
            if update_data():
                line.set_data(self.x_data, self.y_data)
                subplot.relim()
                subplot.autoscale_view(True, True, True)
                figure.canvas.restore_region(background)
                debug_lines[1] = "Data Points:%d" % _len(self.x_queue)
                figure.draw_artist(subplot)
                blit(subplot_bbox)
            else:
                figure.canvas.restore_region(background)
                subplot.draw_artist(debug_text)
                blit(debug_text.get_window_extent())

            flush_events()
            frames += 1

    def update_data(self):
        with self.data_lock:
            if self.client.have_update:
                self.x_data = self.x_queue.get()
                self.y_data = self.y_queue.get()
                txt1 = "Current Queue Read: %d" % (len(self.x_data))
                self.debug_lines[2] = txt1
                assert len(self.x_data) == len(self.y_data)
                self.client.have_update = False
                return True
        return False


class Client():
    OP_XY = 0
    OP_XYL = 1
    OP_XLYL = 2
    OP_EXIT = 3

    def __init__(self, addr, x_q, y_q, dlock):
        """
        :param addr: address for socket.socket()
        :type addr: (str, int)
        :param x_q: x data queue
        :type x_q: RingBuffer
        :param y_q: y data queue
        :type y_q: RingBuffer
        :param dlock: data lock
        :type dlock: threading.Lock
        """
        self.dlock = dlock
        self.x_q = x_q
        self.y_q = y_q
        self.addr = addr
        self.thread = None
        self.sock = socket.socket()
        self.sock.connect(addr)
        self.rfile = self.sock.makefile('rb')
        self.running = 1
        self.have_update = False

    def start(self):
        self.thread = threading.Thread(None, self.pump_data, "RTPlotClientThread", daemon=True)
        self.thread.start()

    def pump_data(self):
        put_x = self.x_q.put
        put_y = self.y_q.put
        lock = self.dlock
        while True:
            code, data = pickle.load(self.rfile)
            if code == self.OP_XY:
                x, y = data
                with lock:
                    put_x(x)
                    put_y(y)
                self.have_update = True
            elif code == self.OP_XYL:
                for x, y in data:
                    with lock:
                        put_x(x); put_y(y)
                self.have_update = True
            elif code == self.OP_XLYL:
                x_data, y_data = data
                with lock:
                    for x in x_data:
                        put_x(x)
                    for y in y_data:
                        put_y(y)
                self.have_update = True
            elif code == self.OP_EXIT:
                break
            else:
                raise ValueError(code)


def start_client(argv):
    host = argv[1]
    port = int(argv[2])
    logger.debug("")
    addr = (host, port)
    plotter = RTPlotter(addr, 1000, 'ggplot')
    plotter.run_forever()

if __name__ == '__main__':
    start_client()
