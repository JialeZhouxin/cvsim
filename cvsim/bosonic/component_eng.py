"""Pure component-engineering helpers for the Bosonic representation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cvsim.bosonic.state import BosonicState, Component, weight_sum


@dataclass(frozen=True)
class LeakReport:
    """Observable quality report returned by component-reducing operations."""

    input_components: int = 0
    output_components: int = 0
    dropped_components: int = 0
    dropped_weight_mass: float = 0.0
    merge_groups: int = 0
    merge_distortion: float = 0.0
    warning: bool = False


def _validate_weights(state: BosonicState) -> None:
    """Reject non-finite component weights before numerical operations."""
    if any(not np.isfinite(component.w) for component in state.components):
        raise ValueError("component weights must be finite")


def _copy_component(component: Component, *, w: complex | None = None) -> Component:
    return Component(
        V=component.V.copy(),
        rbar=component.rbar.copy(),
        w=component.w if w is None else w,
    )


def normalize(state: BosonicState, *, atol: float = 1e-12) -> BosonicState:
    """Return a copy whose component weights sum to one.

    The normalization criterion is the complex sum ``Σw``. Component geometry
    is copied unchanged and the input state is never modified.
    """
    _validate_weights(state)
    total = weight_sum(state)
    if abs(total) <= atol:
        raise ValueError("weight sum is zero")
    return BosonicState(
        [
            _copy_component(component, w=component.w / total)
            for component in state.components
        ]
    )


def merge(
    state: BosonicState,
    *,
    atol: float = 1e-10,
    rtol: float = 1e-8,
) -> tuple[BosonicState, LeakReport]:
    """Merge geometrically close components with stable greedy grouping.

    The first component in each group is retained as the representative;
    only its covariance and mean are copied to the result.
    """
    _validate_weights(state)
    if not state.components:
        return BosonicState([]), LeakReport()

    groups: list[list[Component]] = []
    for component in state.components:
        for group in groups:
            representative = group[0]
            if np.allclose(
                representative.V,
                component.V,
                atol=atol,
                rtol=rtol,
            ) and np.allclose(
                representative.rbar,
                component.rbar,
                atol=atol,
                rtol=rtol,
            ):
                group.append(component)
                break
        else:
            groups.append([component])

    merged_components: list[Component] = []
    merge_groups = 0
    max_distortion = 0.0
    for group in groups:
        representative = group[0]
        if len(group) > 1:
            merge_groups += 1
        for component in group[1:]:
            max_distortion = max(
                max_distortion,
                float(np.max(np.abs(component.V - representative.V))),
                float(np.max(np.abs(component.rbar - representative.rbar))),
            )
        merged_components.append(
            _copy_component(representative, w=sum(component.w for component in group))
        )

    return BosonicState(merged_components), LeakReport(
        input_components=len(state.components),
        output_components=len(merged_components),
        merge_groups=merge_groups,
        merge_distortion=max_distortion,
    )


def truncate(
    state: BosonicState,
    *,
    amp_cutoff: float = 1e-6,
    validate: bool = False,
    warn_threshold: float = 1e-6,
    fail_threshold: float = 1e-3,
) -> tuple[BosonicState, LeakReport]:
    """Drop components with ``abs(w) < amp_cutoff`` and report the loss."""
    _validate_weights(state)
    thresholds = (amp_cutoff, warn_threshold, fail_threshold)
    if any(not np.isfinite(value) or value < 0.0 for value in thresholds):
        raise ValueError("cutoff and leakage thresholds must be finite and non-negative")

    kept = [component for component in state.components if abs(component.w) >= amp_cutoff]
    dropped = [component for component in state.components if abs(component.w) < amp_cutoff]
    dropped_mass = float(sum(abs(component.w) for component in dropped))
    warning = dropped_mass > warn_threshold
    if dropped_mass > fail_threshold or (validate and warning):
        threshold = fail_threshold if dropped_mass > fail_threshold else warn_threshold
        raise ValueError(
            f"truncation leakage {dropped_mass:.3g} exceeds fail threshold {threshold}"
        )
    if warning:
        import warnings

        warnings.warn(
            f"truncation leakage {dropped_mass:.3g} above warn threshold {warn_threshold}",
            RuntimeWarning,
            stacklevel=2,
        )

    output = BosonicState([_copy_component(component) for component in kept])
    return output, LeakReport(
        input_components=len(state.components),
        output_components=len(kept),
        dropped_components=len(dropped),
        dropped_weight_mass=dropped_mass,
        warning=warning,
    )


def is_hermitian(
    state: BosonicState,
    *,
    atol: float = 1e-10,
    rtol: float = 1e-8,
) -> bool:
    """Check that components close under conjugation.

    A component is paired with another component having the same covariance,
    conjugate mean, and conjugate weight. Real components may pair with
    themselves. Matching is one-to-one, so duplicate components cannot mask
    an unmatched component.
    """
    _validate_weights(state)
    components = state.components
    used: set[int] = set()
    for index, component in enumerate(components):
        if index in used:
            continue
        partner = next(
            (
                candidate_index
                for candidate_index, candidate in enumerate(components)
                if candidate_index not in used
                and np.allclose(candidate.V, component.V, atol=atol, rtol=rtol)
                and np.allclose(
                    candidate.rbar,
                    component.rbar.conjugate(),
                    atol=atol,
                    rtol=rtol,
                )
                and np.allclose(
                    candidate.w,
                    component.w.conjugate(),
                    atol=atol,
                    rtol=rtol,
                )
            ),
            None,
        )
        if partner is None:
            return False
        used.add(index)
        used.add(partner)
    return True


__all__ = ["LeakReport", "normalize", "is_hermitian", "merge", "truncate"]
