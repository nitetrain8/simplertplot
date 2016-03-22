"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition


"""
import threading
from time import sleep

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


class _StopEventLoop(Exception):
    pass


class _ExitThread(Exception):
    pass


_event_loop = None


def get_event_loop():
    global _event_loop
    if _event_loop is None:
        _event_loop = ThreadedEventLoop()
    return _event_loop


class EventLoop():
    def __init__(self):
        self.workers = set()
        self._idle = False
        self.idle_sleeptime = .1
        self.run_forever = self.start

    def start(self):
        self.mainloop()

    def stop(self):
        raise _StopEventLoop

    def mainloop(self):
        while True:
            try:
                self._inner_mainloop()
            except _StopEventLoop:
                logger.debug("StopEventLoop", exc_info=True)
                self._idle = True
            except _ExitThread:
                logger.debug("Got Exit Thread signal", exc_info=True)
                return
            while self._idle:
                self._sleep_idle()

    def _sleep_idle(self):
        sleep(self.idle_sleeptime)

    def _inner_mainloop(self):
        while True:
            self._check_running()
            if not self.workers:
                self._sleep_idle()
                continue
            workers = self.workers.copy()

            for w in workers:
                rv = self._run_worker(w)
                if rv is False:
                    self.workers.remove(w)

    def _check_running(self):
        pass

    def _run_worker(self, w):
        try:
            return w()
        except StopIteration:
            logger.debug("Worker raised StopIteration: %s", w)
            return False
        except Exception:
            logger.exception("Exception in event loop")
            return False

    def add_worker(self, w):
        self.workers.add(w)

    def remove_worker(self, w):
        try:
            self.workers.remove(w)
        except KeyError:
            logger.warning("Attempted to remove non-existent worker: %s", w)


class ThreadedEventLoop(EventLoop):

    def __init__(self, client_side=False):
        super().__init__()
        self.client_side = client_side
        self.thread = None
        self.start()

    def start(self):
        if self.thread and self.thread.is_alive():
            self._idle = False
        else:
            self.thread = threading.Thread(None, self.mainloop, "RTPlot%sThread" %
                                           ("Client" if self.client_side else "Server"), daemon=True)
            self.thread.start()

