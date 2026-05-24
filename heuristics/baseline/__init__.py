"""Baseline priority functions. Higher priority = place next.

Each baseline lives in its own module so students can read them one at a
time and add new heuristics by dropping in a new file.
"""

from .edd             import edd
from .least_slack     import least_slack
from .lpt             import lpt
from .random_priority import random_priority
from .spt             import spt

__all__ = ["edd", "least_slack", "lpt", "random_priority", "spt"]
