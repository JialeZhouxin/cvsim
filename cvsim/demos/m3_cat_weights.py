"""M3 AC: small cat 4-component structure + weight sum ≈ 1."""

from __future__ import annotations

from cvsim.bosonic import even_cat, odd_cat, weight_sum

ATOL = 1e-12
ALPHA = 0.8


def check_cat(name: str, even: bool) -> None:
    st = even_cat(ALPHA) if even else odd_cat(ALPHA)
    print(f"{name}  α={ALPHA}  K={st.n_components}")
    assert st.n_components == 4, "expect 4 components (diag+cross)"

    ws = [c.w for c in st.components]
    rs = [c.rbar for c in st.components]
    for i, (w, r) in enumerate(zip(ws, rs, strict=False)):
        print(f"  [{i}] w={w:.6g}  rbar={r}")

    # diagonal: real positive centres on ±x; cross: imag on p
    assert abs(rs[0][0].real) > 0 and abs(rs[0][1]) < ATOL
    assert abs(rs[1][0].real) > 0 and abs(rs[1][1]) < ATOL
    assert abs(rs[0][0] + rs[1][0]) < ATOL  # opposite peaks
    assert abs(rs[2][0]) < ATOL and abs(rs[2][1].imag) > 0
    assert abs(rs[3][0]) < ATOL and abs(rs[3][1].imag) > 0

    # diag weights real positive; even cross + , odd cross −
    assert abs(ws[0].imag) < ATOL and ws[0].real > 0
    assert abs(ws[1] - ws[0]) < ATOL
    if even:
        assert ws[2].real > 0
    else:
        assert ws[2].real < 0

    s = weight_sum(st)
    print(f"  sum w = {s}")
    assert abs(s - 1.0) < ATOL, f"weight sum {s} != 1"
    print(f"  OK {name}")


def main() -> None:
    print("M3 Bosonic cat weights")
    check_cat("even_cat", even=True)
    check_cat("odd_cat", even=False)
    print("OK: AC3.1–3.2 passed")


if __name__ == "__main__":
    main()
