"""Compat re-export. Prefer `cvsim.symplectic` for new code.

This shim mirrors the full public surface of `cvsim.symplectic` so that
`from cvsim.gaussian.symplectic import is_symplectic, S_CZ, ...` keeps working.
"""

from cvsim.symplectic import (  # noqa: F401
    S_beamsplitter,
    S_CX,
    S_CZ,
    S_phase,
    S_squeeze,
    S_two_mode_squeeze,
    d_displace,
    is_symplectic,
    validate_symplectic,
)

__all__ = [
    "d_displace",
    "is_symplectic",
    "validate_symplectic",
    "S_squeeze",
    "S_phase",
    "S_beamsplitter",
    "S_two_mode_squeeze",
    "S_CZ",
    "S_CX",
]
