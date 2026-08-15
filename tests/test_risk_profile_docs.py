"""
Risk profile documentation drift test
─────────────────────────────────────
CLAUDE.md's risk profile table drifted away from config/risk_profiles.py until
every row was wrong (LOW's PUT threshold, all three afternoon cuts, HIGH's
thresholds and trade cap). Docs that quietly disagree with the code are worse
than no docs, because tuning decisions get made against the wrong numbers.

This asserts the table still matches the dataclasses.

Run:
  python tests/test_risk_profile_docs.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.risk_profiles import LOW_RISK, MEDIUM_RISK, HIGH_RISK

CLAUDE_MD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CLAUDE.md")
MARKET_OPEN_MINUTES = 9 * 60 + 15  # 9:15 IST


def _ist(minutes_from_open: int) -> str:
    total = MARKET_OPEN_MINUTES + minutes_from_open
    return f"{total // 60}:{total % 60:02d}"


def _doc_rows() -> dict:
    """Parse the risk profile table out of CLAUDE.md."""
    text = open(CLAUDE_MD, encoding="utf-8").read()
    rows = {}
    # | LOW (Conservative) | 0.70 / 0.78 | 15% | 50% | 3 | 12:00 IST | Rs200 | 0.8% |
    pattern = re.compile(
        r"^\|\s*(LOW|MEDIUM|HIGH)\s*\([^)]*\)\s*\|"
        r"\s*([\d.]+)\s*/\s*([\d.]+)\s*\|"      # call / put threshold
        r"\s*(\d+)%\s*\|"                        # sl
        r"\s*(\d+)%\s*\|"                        # tgt
        r"\s*(\d+)\s*\|"                         # max trades
        r"\s*(\d+:\d\d)\s*IST\s*\|",             # afternoon cut
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        rows[m.group(1)] = {
            "score_threshold": float(m.group(2)),
            "put_score_threshold": float(m.group(3)),
            "sl_pct": int(m.group(4)) / 100,
            "tgt_pct": int(m.group(5)) / 100,
            "max_trades_day": int(m.group(6)),
            "afternoon_cut_ist": m.group(7),
        }
    return rows


def test_claude_md_table_matches_code():
    docs = _doc_rows()
    assert len(docs) == 3, f"expected 3 profile rows in CLAUDE.md, parsed {len(docs)}: {list(docs)}"

    mismatches = []
    for name, profile in (("LOW", LOW_RISK), ("MEDIUM", MEDIUM_RISK), ("HIGH", HIGH_RISK)):
        doc = docs[name]
        expected = {
            "score_threshold": profile.score_threshold,
            "put_score_threshold": profile.put_score_threshold,
            "sl_pct": profile.sl_pct,
            "tgt_pct": profile.tgt_pct,
            "max_trades_day": profile.max_trades_day,
            "afternoon_cut_ist": _ist(profile.afternoon_cut),
        }
        for field, want in expected.items():
            got = doc[field]
            if isinstance(want, float):
                differs = abs(got - want) > 1e-9
            else:
                differs = got != want
            if differs:
                mismatches.append(f"    {name}.{field}: CLAUDE.md={got!r} code={want!r}")

    assert not mismatches, "CLAUDE.md risk table is stale:\n" + "\n".join(mismatches)
    print(f"  ok: all 3 profiles in CLAUDE.md match config/risk_profiles.py")


def test_high_medium_convergence_is_documented():
    """
    HIGH and MEDIUM currently share every signal filter. That is surprising
    enough that it must stay called out in the docs - if someone re-separates
    them, this test fails and the note gets removed deliberately.
    """
    signal_filters = lambda p: (
        p.score_threshold, p.put_score_threshold,
        p.max_trades_day, p.afternoon_cut, p.max_premium,
    )
    converged = signal_filters(MEDIUM_RISK) == signal_filters(HIGH_RISK)
    text = open(CLAUDE_MD, encoding="utf-8").read()
    documented = "identical on every signal filter" in text

    assert converged == documented, (
        "HIGH/MEDIUM converged=%s but CLAUDE.md documents it=%s - update the note"
        % (converged, documented)
    )
    print(f"  ok: HIGH/MEDIUM convergence ({converged}) matches the doc note")


if __name__ == "__main__":
    failures = 0
    for fn in (test_claude_md_table_matches_code, test_high_medium_convergence_is_documented):
        print(f"\n{fn.__name__}")
        try:
            fn()
        except AssertionError as e:
            failures += 1
            print(f"  FAIL: {e}")

    print("\n" + "=" * 60)
    print("ALL PASSED" if failures == 0 else f"{failures} FAILED")
    sys.exit(1 if failures else 0)
