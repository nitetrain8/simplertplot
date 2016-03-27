"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition


"""
import queue
import threading
import time
import tkinter as tk

from matplotlib import pyplot
import matplotlib.transforms
from matplotlib.ticker import NullFormatter, NullLocator

from simplertplot.queues import RingBuffer
from simplertplot.protocols import XYPlotterProtocol, RPCRequest, RPCResponse

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

    def __init__(self, transport, max_pts, style):
        self.max_pts = max_pts
        self.style = style
        self.transport = transport

    def setup_pyplot(self):
        raise NotImplementedError

    def run_forever(self):
        raise NotImplementedError

    def start_client(self):
        raise NotImplementedError

    def run_plot(self):
        raise NotImplementedError

    def update_data(self):
        raise NotImplementedError


class XYPlotter(BasePlotter):
    """ Actual plotter process, running in spawned thread
    :ivar client: consumer protocol
    :type client: worker.ConsumerClientWorker
    """

    def __init__(self, transport, max_pts=1000, style='ggplot'):
        super().__init__(transport, max_pts, style)
        assert max_pts > 0, "max_pts < 0: %s" % max_pts
        self.x_queue = RingBuffer(max_pts)
        self.y_queue = RingBuffer(max_pts)
        self.rpc_req = queue.Queue()
        self.rpc_rsp = queue.Queue()
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
        self.client = XYPlotterProtocol(self.x_queue, self.y_queue, self.rpc_req, self.rpc_rsp)
        self.client.connection_made(transport)

    def clear_pyplot(self):
        if self.figure:
            pyplot.close(self.figure)
        self.figure = None
        self.subplot = None
        self.fps_text = None
        self.npts_text = None
        self.debug_text = None

    def destroy(self):
        """ Destroy the plot, freeing all references """
        while self.__dict__:
            self.__dict__.pop()

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
        from simplertplot import manager
        manager.get_process_manager().run_protocol(self.client)

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
        r = figure.canvas.renderer
        subplot = self.subplot

        xaxis = subplot.xaxis
        yaxis = subplot.yaxis
        bboxes = xaxis.get_window_extent(r), yaxis.get_window_extent(r), subplot.bbox
        all_bbox = matplotlib.transforms.Bbox.union(bboxes)

        # The following is a (hack?) to obtain a copy of the canvas background
        # without the ticks or tick labels, to allow tick label blitting to
        # work correctly. Without this, the copy_from_background() method copies
        # a background that has the default tick marks in place, which causes blit()
        # updates to be drawn on top of a background containing existing tick marks.
        # So, ticks are hidden, the emtpy canvas is redrawn, background is cached, and
        # then ticks are restored.

        xmjf = xaxis.get_major_formatter()
        xmjl = xaxis.get_major_locator()
        ymjf = yaxis.get_major_formatter()
        ymjl = yaxis.get_major_locator()
        xaxis.set_major_formatter(NullFormatter())
        xaxis.set_major_locator(NullLocator())
        yaxis.set_major_formatter(NullFormatter())
        yaxis.set_major_locator(NullLocator())

        figure.canvas.draw()
        background = figure.canvas.copy_from_bbox(all_bbox)

        xaxis.set_major_formatter(xmjf)
        xaxis.set_major_locator(xmjl)
        yaxis.set_major_formatter(ymjf)
        yaxis.set_major_locator(ymjl)

        figure.draw(r)

        frames = 0
        update_data = self.update_data

        line, = subplot.plot(self.x_data, self.y_data)
        line.background = background
        debug_text = self.debug_text
        debug_lines = self.debug_lines
        process_rpc = self.process_rpc

        blit = self.figure.canvas.blit
        flush_events = figure.canvas.flush_events

        _len = len
        _time = time.time
        start = _time()
        # avoid ZeroDivisionError on floating point arithmetic for fps calc
        while not (_time() - start):
            pass

        subplot.set_ymargin(0.02)

        # mainloop
        while True:
            process_rpc()
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
                figure.draw_artist(xaxis)
                figure.draw_artist(yaxis)
                figure.draw_artist(line)
                figure.draw_artist(debug_text)
                blit(all_bbox)
                blit(yaxis.get_window_extent(r))
            else:
                figure.canvas.restore_region(background)
                subplot.draw_artist(debug_text)
                blit(debug_text.get_window_extent())

            flush_events()
            frames += 1

    def update_data(self):
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

    def process_rpc(self):
        try:
            req = self.rpc_req.get(False)
        except queue.Empty:
            return
        else:
            try:
                func = getattr(self, req.func)
                rv = func(*req.args, **req.kwargs)
            except Exception as e:
                rsp = req.respond(exc=e)
            else:
                rsp = req.respond(value=rv)
            self.rpc_rsp.put(rsp)

    def test_rpc(self, msg):
        print("GOT RPC MSG:", msg)
        return len(msg)


class _DummyPlotter(XYPlotter):
    def run_plot(self):
        yield
        i = 1
        self.update_data(i)
        self.process_rpc()
        i += 1

    def update_data(self, i):
        print("\rUpdated data: %d" % i, end="")



class _EchoPlot(BasePlotter):
    """ Plot that echos received data instead of
    plotting it. Used for internal debugging. """

    def __init__(self, transport, max_pts, style):
        from . import transport
        super().__init__(transport, max_pts, style)
        self.transport = transport.SocketTransport.from_address(transport)
        self.reader = self.writer = self.transport

    def pong(self):
        if not self.transport.read_ready():
            return
        mlen = self.reader.read(3)
        mlen = int(mlen)
        msg = self.reader.read(mlen)
        if msg.lower() == b'SYS_EXIT'.lower():
            raise SystemExit(0)
        self.writer.write(msg)

    def run_forever(self):
        while True:
            self.pong()

    def run_plot(self):
        pass

    def update_data(self):
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
