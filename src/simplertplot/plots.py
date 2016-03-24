"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition


"""
import threading
import time
import tkinter as tk

from matplotlib import pyplot

from simplertplot.queues import RingBuffer
from simplertplot.workers import TCPPlotServerProtocol

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


class BasePlotter():

    def __init__(self, addr, max_pts, style):
        self.max_pts = max_pts
        self.style = style
        self.addr = addr

    def setup_pyplot(self):
        raise NotImplementedError

    def run_forever(self):
        raise NotImplementedError

    def start_client(self):
        raise NotImplementedError

    def run_plot(self):
        raise NotImplementedError

    def check_update(self):
        raise NotImplementedError


class XYPlotter(BasePlotter):
    """ Actual plotter process, running in spawned thread
    :ivar client: consumer protocol
    :type client: worker.ConsumerClientWorker
    """

    def __init__(self, addr, max_pts=1000, style='ggplot'):
        super().__init__(addr, max_pts, style)
        assert max_pts > 0, "max_pts < 0: %s" % max_pts
        self.x_queue = RingBuffer(max_pts)
        self.y_queue = RingBuffer(max_pts)
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
        self.client = TCPPlotServerProtocol(self.addr, self.x_queue, self.y_queue)

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

    def start_client(self):
        self.client.start()

    def run_forever(self):
        self.setup_pyplot()
        self.start_client()
        try:
            self.run_plot()
        except tk.TclError:
            pass
        except Exception:  # often throws on shutdown
            logger.exception("Exception in run-plot mainloop")
            raise

    def run_plot(self):

        figure = self.figure
        figure.show()
        figure.draw(figure.canvas.renderer)

        frames = 0
        check_update = self.check_update

        subplot = self.subplot
        line, = subplot.plot(self.x_data, self.y_data)
        background = figure.canvas.copy_from_bbox(subplot.bbox)
        debug_text = self.debug_text
        debug_lines = self.debug_lines

        blit = self.figure.canvas.blit
        subplot_bbox = self.subplot.bbox
        flush_events = figure.canvas.flush_events
        xaxis = subplot.xaxis
        yaxis = subplot.yaxis

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
            if check_update():
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

    def check_update(self):
        with self.client.lock_queue():
            if self.client.current_update:
                self.x_data = self.x_queue.get()
                self.y_data = self.y_queue.get()
                txt1 = "Current Queue Read: %d" % self.client.current_update
                self.debug_lines[2] = txt1
                assert len(self.x_data) == len(self.y_data)
                self.client.current_update = 0
                return True
        return False


class _EchoPlot(BasePlotter):
    """ Plot that echos received data instead of
    plotting it. Used for internal debugging. """

    def __init__(self, addr, max_pts, style):
        import socket
        super().__init__(addr, max_pts, style)
        self.sock = socket.socket()
        self.sock.connect(addr)
        self.writer = self.sock.makefile('wb')
        self.reader = self.sock.makefile('rb')

    def pong(self):
        import select
        r, _, _ = select.select((self.sock,), (), (), 1)
        if self.sock not in r:
            return
        mlen = self.reader.read(3)
        mlen = int(mlen)
        msg = self.reader.read(mlen)
        if msg.lower() == b'SYS_EXIT'.lower():
            raise SystemExit(0)
        self.writer.write(msg)
        self.writer.flush()

    def run_forever(self):
        while True:
            self.pong()

    def run_plot(self):
        pass

    def check_update(self):
        pass

    def setup_pyplot(self):
        pass

    def start_client(self):
        pass


def get_plot_mapping():
    plots = {
        'xyplotter': XYPlotter,
        'echo': _EchoPlot
    }
    return plots


def get_plot_class(name):
    return get_plot_mapping()[name]
