# PRD: Phase1 F-INTERFEROMETER + F-GATE-SET tail

## Goal

Passive linear optics from unitary \(U\) plus thin gate aliases `fourier` / `mach_zehnder`, per vision §4.1.

## In

1. `S_from_unitary(U)` + unitary validation → xxpp symplectic
2. `apply_interferometer(state, U)` / `interferometer(state, U)`
3. `fourier(state, mode)` = phase(π/2)
4. `mach_zehnder(state, m1, m2, theta, phi)` documented BS+phase composition
5. Phase-1 target: `clements_decomposition` **or** documented Reck alt with round-trip test
6. Exports + tests (Haar U m=2,4,8; TMSV+BS; fourier^4; MZ vs manual)

## Out

- General (X,Y) channels (next task)
- Circuit DSL methods (optional follow-up)
- Compile merge S

## Acceptance

1. `S_from_unitary(I)=I`; result always symplectic when U unitary
2. Non-unitary U raises
3. Library BS matches embed of its defining 2×2 U
4. Haar random U m∈{2,4,8}: symplectic + apply preserves purity on vacuum
5. Decomposition recomposes to U (Frobenius)
6. Full pytest green
