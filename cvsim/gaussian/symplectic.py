"""Compat re-export. Prefer `cvsim.symplectic`."""

from cvsim.symplectic import (  # noqa: F401
    S_beamsplitter,
    S_phase,
    S_squeeze,
    S_two_mode_squeeze,
    d_displace,
)

__all__ = [
    "d_displace",
    "S_squeeze",
    "S_phase",
    "S_beamsplitter",
    "S_two_mode_squeeze",
]
