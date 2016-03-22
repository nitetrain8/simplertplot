"""

Created by: Nathan Starkweather
Created on: 03/21/2016
Created in: PyCharm Community Edition


"""
import queue
import socket
from select import select

from simplertplot import client_plotter

__author__ = 'Nathan Starkweather'

import logging
import sys
import subprocess

logger = logging.getLogger(__name__)
_h = logging.StreamHandler()
_f = logging.Formatter("%(created)s %(name)s %(levelname)s (%(lineno)s): %(message)s")
_h.setFormatter(_f)
logger.addHandler(_h)
logger.propagate = False
logger.setLevel(logging.DEBUG)
del _h, _f

from . import transport
from . import util
from . import protocol
from . import serializer
from . import eventloop
from . import userplot

_g_manager = None


def get_manager():
    global _g_manager
    if _g_manager is None:
        _g_manager = PlotProcessManager(False)
    assert isinstance(_g_manager, PlotProcessManager)
    return _g_manager


def create_client_manager(addr):
    global _g_manager
    if _g_manager is None:
        _g_manager = PlotProcessManager(True, addr)
    assert isinstance(_g_manager, PlotProcessManager)
    return _g_manager


_spawn_src = """
from simplertplot import client_process
import sys
client_process.startup_client(sys.argv)"""


class _ManagerCom():
    def __init__(self, sock):
        self.sock = sock
        self.addr = self.sock.getsockname()
        self.rfile = sock.makefile('rb')
        self.wfile = sock.makefile('wb')
        self.serializer = serializer.PickleSerializer()

    def send_op(self, op, arg=None):
        data = (op, arg)
        self.serializer.dump(data, self.wfile)
        self.wfile.flush()

    def recv_op(self):
        op, arg = self.serializer.load(self.rfile)
        return op, arg

    def reconnect(self):
        family = self.sock.family
        type = self.sock.type
        proto = self.sock.proto
        self.sock = socket.socket(family, type, proto)
        self.addr = self.sock.getsockname()


class PlotProcessManager():
    # message opcodes

    NEW_CLIENT = 0
    SHUTDOWN = 1

    def __init__(self, client_side=False, server_addr=None):
        """
        :param client_side: simple boolean to indicate whether we're the client
                            or user-side process manager.
        :type client_side: bool
        """
        self.addr = server_addr
        self.client_side = client_side
        self.popen = None
        self.thread = None
        self.plots = set()
        self.com_channel = None
        self.message_loop = None
        self.plot_loop = None
        self.server = None
        self.spawn_message_pump()
        if self.client_side:
            assert server_addr
            self.reconnect_server()
            self.spawn_plot_loop()
            self.plot_loop.add_worker(self.client_listener)

    def reconnect_server(self):
        s = socket.socket()
        s.connect(self.addr)
        self.com_channel = _ManagerCom(s)

    def start_process(self):
        if self.popen:
            raise RuntimeError("Process already started")
        python = sys.executable
        if self.addr:
            host, port = self.addr
            self.server = transport.SimpleServer(host, port)
        else:
            host = 'localhost'
            self.server = transport.SimpleServer(host)
            host, port = self.server.get_addr()
        cmd = "%s -c %s %s %d" % (util.quote(python), util.quote(_spawn_src), host, port)
        self.popen = subprocess.Popen(cmd)
        sock = self.server.accept_connection(False)
        self.com_channel = _ManagerCom(sock)

    def new_user_plot(self, plot, queue_size):
        if self.popen is None: self.start_process()
        self.plots.add(plot)
        client_sock = self.request_new_client()
        q = queue.Queue(queue_size)
        proto = protocol.UserSideProtocol(client_sock, q, loop=self.message_loop)
        return proto, q

    def request_new_client(self):
        self.com_channel.send_op(self.NEW_CLIENT, None)
        new_sock = self.server.accept_connection(False)
        return new_sock

    def client_listener(self):
        r, w, x = select((self.com_channel.sock,), (), ())
        if self.com_channel.sock in r:
            op, arg = self.com_channel.recv_op()
            if op == self.NEW_CLIENT:
                logger.debug("OP_NEW_CLIENT")
                s = socket.socket()
                s.connect(self.addr)
                proto = protocol.ClientSideProtocol(s, loop=self.message_loop)
                plot = proto.handshake()
                self.plot_loop.add_worker(plot.run_plot())
                self.plots.add(plot)
                proto.start()

    def _reg_new_client_plot(self, plot):
        self.plots.add(plot)
        self.plot_loop.add_worker(plot.run_plot())

    def spawn_message_pump(self):
        loop = eventloop.ThreadedEventLoop(self.client_side)
        loop.start()
        self.message_loop = loop

    def spawn_plot_loop(self):
        self.plot_loop = eventloop.EventLoop()

    def run_plot_loop(self):
        for p in self.plots:
            self.plot_loop.add_worker(p.run_plot())
        self.plot_loop.run_forever()

