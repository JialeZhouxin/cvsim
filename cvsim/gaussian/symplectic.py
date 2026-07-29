"""Compat re-export. Prefer `cvsim.symplectic` for new code.

This shim mirrors the full public surface of `cvsim.symplectic` so that
`from cvsim.gaussian.symplectic import is_symplectic, S_CZ, ...` keeps working.
"""

from cvsim.symplectic import (  # noqa: F401
    S_beamsplitter,
    S_CX,
    S_CZ,
    S_from_unitary,
    S_mach_zehnder,
    S_phase,
    S_squeeze,
    S_two_mode_squeeze,
    U_beamsplitter,
    clements_decomposition,
    compose_unitary_mesh,
    d_displace,
    embed_U_2mode,
    is_symplectic,
    is_unitary,
    reck_decomposition,
    validate_symplectic,
    validate_unitary,
)

__all__ = [
    "d_displace",
    "is_symplectic",
    "validate_symplectic",
    "is_unitary",
    "validate_unitary",
    "S_from_unitary",
    "U_beamsplitter",
    "embed_U_2mode",
    "reck_decomposition",
    "clements_decomposition",
    "compose_unitary_mesh",
    "S_mach_zehnder",
    "S_squeeze",
    "S_phase",
    "S_beamsplitter",
    "S_two_mode_squeeze",
    "S_CZ",
    "S_CX",
]
