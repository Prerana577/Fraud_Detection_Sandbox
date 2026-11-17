# rules/__init__.py
# Makes the rules directory a Python package.
# Import all rule functions here so scoring.py can iterate over them easily.

from .impossible_travel import check_impossible_travel
from .velocity import check_velocity
from .amount_anomaly import check_amount_anomaly
from .repeated_failures import check_repeated_failures

# Ordered list of rule checkers used by scoring.py
ALL_RULES = [
    check_impossible_travel,
    check_velocity,
    check_amount_anomaly,
    check_repeated_failures,
]
