"""B2 component invariants and engineering tests."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from cvsim.bosonic.component_eng import (
    LeakReport,
    is_hermitian,
    merge,
    normalize,
    truncate,
)
from cvsim.bosonic.state import BosonicState, Component, weight_sum

pytestmark = pytest.mark.phaseB2


def _component(*, rbar=None, w=1.0 + 0.0j, delta=0.0) -> Component:
    return Component(
        V=np.diag([0.5 + delta, 0.5 + delta]),
        rbar=np.array([0.2 + 0.1j, -0.3 + 0.2j] if rbar is None else rbar),
        w=w,
    )


def test_leak_report_is_frozen_and_has_empty_defaults():
    report = LeakReport()

    assert report.input_components == 0
    assert report.output_components == 0
    assert report.dropped_components == 0
    assert report.dropped_weight_mass == 0.0
    assert report.merge_groups == 0
    assert report.merge_distortion == 0.0
    assert report.warning is False
    with pytest.raises(FrozenInstanceError):
        report.warning = True


def test_normalize_uses_complex_weight_sum_without_mutating_input():
    first = _component(w=0.25 + 0.1j)
    second = _component(rbar=[0.4 - 0.2j, 0.1 + 0.3j], w=0.75 - 0.1j)
    state = BosonicState([first, second])
    original_weights = [component.w for component in state.components]
    original_v = [component.V.copy() for component in state.components]
    original_rbar = [component.rbar.copy() for component in state.components]

    normalized = normalize(state)

    assert normalized is not state
    assert weight_sum(normalized) == pytest.approx(1.0)
    assert [component.w for component in state.components] == original_weights
    for component, v, rbar in zip(state.components, original_v, original_rbar, strict=False):
        np.testing.assert_array_equal(component.V, v)
        np.testing.assert_array_equal(component.rbar, rbar)
    for component, source in zip(normalized.components, state.components, strict=False):
        assert component is not source
        np.testing.assert_array_equal(component.V, source.V)
        np.testing.assert_array_equal(component.rbar, source.rbar)


def test_normalize_rejects_empty_and_zero_weight_sum():
    with pytest.raises(ValueError, match="weight sum"):
        normalize(BosonicState([]))
    with pytest.raises(ValueError, match="weight sum"):
        normalize(BosonicState([_component(w=1.0), _component(w=-1.0)]))


@pytest.mark.parametrize("bad_weight", [complex(np.nan, 0.0), complex(np.inf, 0.0)])
def test_component_operations_reject_nonfinite_weights(bad_weight):
    state = BosonicState([_component(w=bad_weight)])

    with pytest.raises(ValueError, match="finite"):
        normalize(state)
    with pytest.raises(ValueError, match="finite"):
        is_hermitian(state)


def test_is_hermitian_accepts_real_component_self_pair():
    assert is_hermitian(BosonicState([_component(rbar=[0.2, -0.3], w=0.5)]))


def test_is_hermitian_accepts_complex_conjugate_pairs():
    component = _component(w=0.4 + 0.2j)
    conjugate = _component(
        rbar=component.rbar.conj(),
        w=component.w.conjugate(),
    )

    assert is_hermitian(BosonicState([component, conjugate]))


def test_is_hermitian_rejects_missing_conjugate_pair():
    assert not is_hermitian(BosonicState([_component(w=0.4 + 0.2j)]))


def test_is_hermitian_matches_v_and_rbar_with_configured_tolerance():
    component = _component(w=0.5 + 0.2j)
    conjugate = _component(
        rbar=component.rbar.conj() + 5e-11,
        w=component.w.conjugate() + 5e-11j,
    )

    state = BosonicState([component, conjugate])
    assert is_hermitian(state)
    assert not is_hermitian(state, atol=1e-12, rtol=0.0)


def test_is_hermitian_rejects_unmatched_component_geometry():
    component = _component(w=0.5 + 0.2j)
    unmatched = _component(rbar=component.rbar.conj() + 1e-3, w=component.w.conjugate())

    assert not is_hermitian(BosonicState([component, unmatched]))


def test_merge_combines_matching_geometry_and_preserves_first_representative():
    first = _component(w=0.2 + 0.1j)
    matching = _component(w=0.3 - 0.1j)
    separate = _component(delta=0.2, w=0.5)
    state = BosonicState([first, matching, separate])

    merged, report = merge(state, atol=1e-10, rtol=0.0)

    assert merged.n_components == 2
    assert [component.w for component in merged.components] == pytest.approx(
        [0.5 + 0.0j, 0.5 + 0.0j]
    )
    np.testing.assert_array_equal(merged.components[0].V, first.V)
    np.testing.assert_array_equal(merged.components[0].rbar, first.rbar)
    assert report.input_components == 3
    assert report.output_components == 2
    assert report.dropped_components == 0
    assert report.dropped_weight_mass == 0.0
    assert report.merge_groups == 1
    assert report.merge_distortion == 0.0


def test_merge_uses_only_geometry_not_weights_and_keeps_input_unchanged():
    state = BosonicState([_component(w=2.0), _component(w=-0.5)])
    original = [
        (c.V.copy(), c.rbar.copy(), c.w) for c in state.components
    ]

    merged, _ = merge(state)

    assert merged.n_components == 1
    assert merged.components[0].w == pytest.approx(1.5)
    for component, (v, rbar, w) in zip(state.components, original, strict=False):
        np.testing.assert_array_equal(component.V, v)
        np.testing.assert_array_equal(component.rbar, rbar)
        assert component.w == w
    assert merged.components[0] is not state.components[0]


def test_merge_is_stable_greedy_not_transitive():
    first = _component(delta=0.0, w=1.0)
    close_to_first = _component(delta=0.75e-10, w=2.0)
    close_only_to_second = _component(delta=1.5e-10, w=4.0)

    merged, report = merge(
        BosonicState([first, close_to_first, close_only_to_second]),
        atol=1e-10,
        rtol=0.0,
    )

    assert merged.n_components == 2
    assert [component.w for component in merged.components] == pytest.approx([3.0, 4.0])
    assert report.merge_groups == 1
    assert report.merge_distortion == pytest.approx(0.75e-10)


def test_merge_empty_state_returns_empty_report():
    merged, report = merge(BosonicState([]))

    assert merged.components == []
    assert report == LeakReport()


def test_truncate_removes_strictly_small_weights_and_reports_mass():
    state = BosonicState(
        [
            _component(w=0.2),
            _component(delta=0.2, w=1e-6),
            _component(delta=0.4, w=-0.25j),
        ]
    )

    truncated, report = truncate(state, amp_cutoff=1e-6)

    assert truncated.n_components == 3
    assert report == LeakReport(input_components=3, output_components=3)
    truncated, report = truncate(state, amp_cutoff=1.0001e-6)
    assert truncated.n_components == 2
    assert report.input_components == 3
    assert report.output_components == 2
    assert report.dropped_components == 1
    assert report.dropped_weight_mass == pytest.approx(1e-6)


def test_truncate_zero_cutoff_keeps_all_components():
    state = BosonicState([_component(w=0.0), _component(delta=0.2, w=1.0)])

    truncated, report = truncate(state, amp_cutoff=0.0)

    assert truncated.n_components == 2
    assert report.dropped_components == 0


def test_truncate_warns_above_warn_threshold():
    state = BosonicState([_component(w=0.0001)])

    with pytest.warns(RuntimeWarning, match="truncation leakage"):
        truncated, report = truncate(state, amp_cutoff=0.0002)

    assert truncated.components == []
    assert report.warning is True
    assert report.dropped_weight_mass == pytest.approx(0.0001)


def test_truncate_strict_validation_and_fail_threshold_raise():
    with pytest.raises(ValueError, match="truncation leakage"):
        truncate(BosonicState([_component(w=0.0001)]), amp_cutoff=0.0002, validate=True)
    with pytest.raises(ValueError, match="truncation leakage"):
        truncate(BosonicState([_component(w=0.6)]), amp_cutoff=0.7, fail_threshold=0.5)


def test_truncate_invalid_parameters_and_weights_raise():
    state = BosonicState([_component(w=1.0)])
    for kwargs in (
        {"amp_cutoff": -1.0},
        {"amp_cutoff": np.inf},
        {"warn_threshold": -1.0},
        {"fail_threshold": np.nan},
    ):
        with pytest.raises(ValueError):
            truncate(state, **kwargs)
    with pytest.raises(ValueError, match="finite"):
        truncate(BosonicState([_component(w=complex(np.inf, 0.0))]))
