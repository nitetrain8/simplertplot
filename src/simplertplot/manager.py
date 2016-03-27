"""

Created by: Nathan Starkweather
Created on: 03/19/2016
Created in: PyCharm Community Edition


"""
import os
import sys
import argparse
import subprocess

import itertools

import time

from simplertplot import transport
from simplertplot import eventloop
from simplertplot import util


__author__ = 'Nathan Starkweather'

import logging

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


_spawn_server_src = """
from simplertplot import manager
m = manager.StartupManager(\\"%s\\", %d, \\"%s\\")
manager._process_manager = m
"""

_spawn_standalone_src = """
from simplertplot import manager
m = manager.StandaloneStartupManager()
manager._process_manager = m
m.run_plot()
"""


class ManagerError(Exception):
    pass


class MngrHandshakeFailure(ManagerError):
    pass


class _SMProxy():
    """ Proxy class representing the StartupManager from user side """
    def __init__(self, sock, name, popen):
        self.popen = popen
        self.name = name
        self.tp = transport.TCPTransport(sock)
        self.write = self.tp.write
        self.read = self.tp.read
        self.readline = self.tp.readline


_user_manager = None
_process_manager = None


def get_user_manager():
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager


def get_process_manager():
    global _process_manager
    return _process_manager


class BaseManager():
    def __init__(self):
        self.proto_event_loop = eventloop.ThreadedEventLoop()

    def run_protocol(self, p):
        self.proto_event_loop.add_worker(p.step_work)

    def stop_protocol(self, p):
        self.proto_event_loop.remove_worker(p.step_work)


class UserManager(BaseManager):

    _spawn_id_counter = itertools.count(1)

    def __init__(self, host='localhost', port=0):
        super().__init__()
        self.manager_server = transport.TCPServer(host, port)
        self.server_procs = []

    def spawn_standalone(self, addr, plot, style, max_pts, mproto, proto_factory):
        python = sys.executable
        host, port = addr
        cmd = "%s -c %s %s %d --plot=%s --mproto=%s --style=%s --max-pts=%d" % (util.quote(python),
                                                        util.quote(_spawn_standalone_src),
                                                        host, port, plot, mproto, style, max_pts)
        self.popen = subprocess.Popen(cmd)
        return self._make_protocol(addr, mproto, proto_factory)

    def _make_protocol(self, addr, mproto, proto_factory):
        t = self._connect_to_standalone_server(addr, mproto)
        f = proto_factory()
        f.connection_made(t)
        return f

    def _connect_to_standalone_server(self, addr, mproto='tcp', timeout=10):
        """ Continuously attempt to connect to a newly spawned server process.
        This is needed to avoid the race condition caused by the user process
        attempting to connect to a server before the child process has
        been able to create it.
        """
        tot = time.time() + timeout
        con = None
        kls = transport.get_transport_class(mproto)
        while time.time() < tot:
            try:
                con = kls.from_address(addr)
            except ConnectionRefusedError:
                pass
            else:
                break
        return con

    def spawn_server(self):
        host, port = self.manager_server.get_addr()
        proc_name = "Serv%03d" % next(self._spawn_id_counter)
        popen = self._spawn_process(host, port, proc_name)
        sock = self.manager_server.accept_connection()
        remote = _SMProxy(sock, proc_name, popen)

        try:
            self._handshake(remote)
        except Exception as e:
            logger.debug("Error in client handshake: %s", e)
        else:
            logger.debug("Successful Handshake")
            self.server_procs.append(remote)

    def wait(self):
        for c in self.server_procs:
            c.popen.wait()

    def kill_all(self):
        for c in self.server_procs:
            c.popen.terminate()

    def _spawn_process(self, host, port, proc_name):
        python = sys.executable
        src = _spawn_server_src % (host, port, proc_name)
        cmd = "%s -c %s" % (util.quote(python), util.quote(src))
        return subprocess.Popen(cmd)

    def _handshake(self, client):
        line = client.tp.readline()
        sm, name, hs = line.strip().split()
        if sm != b'StartupMngr':
            raise MngrHandshakeFailure(sm)
        elif name.decode() != client.name:
            raise MngrHandshakeFailure("%s != %s" % (name, client.name))
        elif hs != b'HANDSHAKE':
            raise MngrHandshakeFailure(hs)
        client.tp.write(b"ACK STARTUP\n")


class StartupManager(BaseManager):
    def __init__(self, host, port, name="unnamed"):
        super().__init__()
        self.name = name
        self.tp = transport.TCPTransport.from_address((host, port))
        try:
            self.handshake()
        except Exception as e:
            logger.debug("Error in server handshake: %s", e)
        else:
            logger.debug("Successful Handshake")
        self.proto_event_loop = eventloop.ThreadedEventLoop()

    def new_plot(self):
        pass

    def detach(self):
        pass

    def handshake(self):
        self.tp.write(("StartupMngr %s HANDSHAKE\n" % self.name).encode('ascii'))
        line = self.tp.readline()
        ack, su = line.strip().split()
        if ack != b"ACK" or su != b"STARTUP":
            raise MngrHandshakeFailure(line)


class StandaloneStartupManager(BaseManager):
    def __init__(self):
        super().__init__()
        ns = self.parse_cmd_line(sys.argv[1:])
        plotter = self.startup_plot(ns)
        self.plotter = plotter

    def run_plot(self):
        self.plotter.client.blocking_io = True
        self.plotter.run_forever()

    def parse_cmd_line(self, args):
        p = argparse.ArgumentParser(description="Launch Real-Time Matplotlib Plot Server")
        p.add_argument("host", type=str.lower)
        p.add_argument("port", type=int)
        p.add_argument("--plot", default="XYPlotter", type=str.lower)
        p.add_argument("--max-pts", default=300000, type=int)
        p.add_argument("--style", default='ggplot', type=str.lower)
        p.add_argument("--mproto", default="tcp", help="Message protocol", choices=("tcp",), type=str.lower)
        rv = p.parse_args(args)
        return rv

    def startup_plot(self, ns):
        from simplertplot import plots
        host = ns.host
        port = ns.port
        plot = ns.plot
        style = ns.style
        max_pts = ns.max_pts
        mproto = ns.mproto

        server_klass = transport.get_server_class(mproto)
        plot_klass = plots.get_plot_class(plot)

        server = server_klass(host, port)
        t = server.accept_connection2()
        plot = plot_klass(t, max_pts, style)

        return plot
