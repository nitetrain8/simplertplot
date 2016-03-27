"""

Created by: Nathan Starkweather
Created on: 03/19/2016
Created in: PyCharm Community Edition


"""
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

from . import util
from . import queues
from . import protocols
from . import eventloop
from . import transport
from . import manager
from . import plots

