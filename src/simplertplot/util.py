"""

Created by: Nathan Starkweather
Created on: 03/20/2016
Created in: PyCharm Community Edition


"""
import io

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


def borrow_docstring(lender, sep='\n\n'):
    def decorator(f):
        buf = io.StringIO()
        buf.write("<Borrowed Docstring>:\n\n")
        buf.write(f.__doc__ or '')
        buf.write(sep if f.__doc__ else '')
        buf.write(lender.__doc__ or "")
        f.__doc__ = buf.getvalue()
        return f

    return decorator
