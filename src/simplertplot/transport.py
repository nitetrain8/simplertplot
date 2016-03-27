"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition


"""
import io

__author__ = 'Nathan Starkweather'

import logging
import socket
import errno
from simplertplot import util
from select import select

logger = logging.getLogger(__name__)
_h = logging.StreamHandler()
_f = logging.Formatter("%(created)s %(name)s %(levelname)s (%(lineno)s): %(message)s")
_h.setFormatter(_f)
logger.addHandler(_h)
logger.propagate = False
logger.setLevel(logging.DEBUG)
del _h, _f


class BaseTransport():
    def connect(self, arg):
        raise NotImplementedError

    def reconnect(self):
        raise NotImplementedError

    def write(self, msg):
        raise NotImplementedError

    def read(self, n=-1):
        raise NotImplementedError

    def read_ready(self):
        raise NotImplementedError

    def write_ready(self):
        raise NotImplementedError


class SocketTransport(BaseTransport):
    sock_type = socket.SOCK_STREAM
    sock_family = socket.AF_INET

    def __init__(self, sock=None):

        self.sock = sock
        self.addr = None
        self.rfile = None

        if self.sock is not None:
            self.addr = sock.getsockname()
            self.rfile = self.sock.makefile('rb')
            self.export_attrs()

    @classmethod
    def from_address(cls, addr):
        self = cls()
        self.connect(addr)
        self.addr = self.sock.getsockname()
        return self

    def connect(self, addr):
        self.sock = socket.socket(self.sock_family, self.sock_type)
        self.sock.connect(addr)
        self.rfile = self.sock.makefile('rb')
        self.export_attrs()

    def reconnect(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            self.sock = None
        except socket.error as e:
            logger.debug("Error closing socket: %s", str(e))
        self.connect(self.addr)

    def export_attrs(self):
        self.read = self.rfile.read
        self.readline = self.rfile.readline

    def write(self, msg):
        return self.sock.sendall(msg)

    def select(self, timeout=0):
        return select((self.sock,), (self.sock,), (), timeout)

    def read_ready(self):
        return self.sock in self.select(0)[0]

    def write_ready(self):
        return self.sock in self.select(0)[1]

    @util.borrow_docstring(io.BufferedReader.readline)
    def readline(self):
        pass

    @util.borrow_docstring(io.BufferedReader.read)
    def read(self, n=-1):
        pass


TCPTransport = SocketTransport


class ServerBase():
    def get_addr(self):
        raise NotImplementedError

    def accept_connection(self, block=True):
        raise NotImplementedError


class TCPServer(ServerBase):
    _transport_factory = TCPTransport

    def __init__(self, host, port=0):
        sock = socket.socket()
        sock.bind((host, port))
        sock.listen(1)
        self.addr = sock.getsockname()
        self.sock = sock

    def get_addr(self):
        return self.addr

    def accept_connection(self, block=True):
        r, w, x = select((self.sock,), (), (), None if block else 0)
        if self.sock in r:
            c, _ = self.sock.accept()
            return c
        return None

    def accept_connection2(self, block=True):
        return self._transport_factory(self.accept_connection(block))


# protocol -> (transport, server)
_transport_classes = {
    'tcp': (SocketTransport, TCPServer)
}


def get_transport_class(name):
    return _transport_classes[name][0]


def get_server_class(name):
    return _transport_classes[name][1]
