"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition


"""
import io

__author__ = 'Nathan Starkweather'

import logging
import socket
from simplertplot import util

logger = logging.getLogger(__name__)
_h = logging.StreamHandler()
_f = logging.Formatter("%(created)s %(name)s %(levelname)s (%(lineno)s): %(message)s")
_h.setFormatter(_f)
logger.addHandler(_h)
logger.propagate = False
logger.setLevel(logging.DEBUG)
del _h, _f


class SocketTransport():
    def __init__(self, addr):
        self.addr = addr
        self.connect()

    def connect(self):
        self.sock = socket.socket()
        self.sock.connect(self.addr)
        self.rfile = self.sock.makefile('rb')
        self.export_attrs()

    def reconnect(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            self.sock = None
        except socket.error as e:
            logger.debug("Error closing socket: %s", str(e))
        self.connect()

    def export_attrs(self):
        self.read = self.rfile.read
        self.readline = self.rfile.readline
        self.send = self.sock.send
        self.sendall = self.sock.sendall
        self.recv = self.sock.recv
        self.recv_into = self.sock.recv_into

    def write(self, msg):
        return self.sock.sendall(msg)

    @util.borrow_docstring(socket.socket.recv_into)
    def recv_into(self, b):
        pass

    @util.borrow_docstring(socket.socket.recv)
    def recv(self, n):
        pass

    @util.borrow_docstring(socket.socket.sendall)
    def sendall(self, msg, flags=0):
        pass

    @util.borrow_docstring(socket.socket.send)
    def send(self, msg, flags=0):
        pass

    @util.borrow_docstring(io.BufferedReader.readline)
    def readline(self):
        pass

    @util.borrow_docstring(io.BufferedReader.read)
    def read(self, n=-1):
        pass

