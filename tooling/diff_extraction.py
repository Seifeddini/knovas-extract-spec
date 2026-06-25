#!/usr/bin/env python3
"""
diff_extraction.py — human-readable diff of an extractor's output vs golden.

Used by language-implementation maintainers when proposing a corpus update
or debugging a golden-test failure. Applies the tolerances from
`MANIFEST.yaml::tolerances` and reports only differences that would FAIL
a golden test, not every byte-level diff.

Usage:

    python diff_extraction.py <actual.json> <expected.json>
    python diff_extraction.py <actual.json> <fixture-path>   # auto-locates expected

Exit codes:
    0 — actual matches expected within tolerance.
    1 — material differences found (test would fail).
    2 — error reading inputs.

Dependencies: PyYAML, python-Levenshtein OR rapidfuzz (for text comparison).
"""
from __future__ import annotations

import json
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    print("ERROR: missing PyYAML.", file=sys.stderr)
    sys.exit(2)

# Levenshtein backend — rapidfuzz preferred (pure-Python, no compile).
try:
    from rapidfuzz.distance import Levenshtein as _Lev  # type: ignore[import-not-found]

    def levenshtein(a: str, b: str) -> int:
        return _Lev.distance(a, b)
except ImportError:  # pragma: no cover
    try:
        import Levenshtein as _Lev_c  # type: ignore[import-not-found]

        def levenshtein(a: str, b: str) -> int:
            return _Lev_c.distance(a, b)
    except ImportError:

        def levenshtein(a: str, b: str) -> int:
            # Fallback: O(n*m) DP. Fine for human-scale diffs.
            if a == b:
                return 0
            if not a:
                return len(b)
            if not b:
                return len(a)
            prev = list(range(len(b) + 1))
            for i, ca in enumerate(a, 1):
                cur = [i] + [0] * len(b)
                for j, cb in enumerate(b, 1):
                    cur[j] = min(
                        prev[j] + 1,
                        cur[j - 1] + 1,
                        prev[j - 1] + (ca != cb),
                    )
                prev = cur
            return prev[-1]


SPEC_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = SPEC_DIR / "MANIFEST.yaml"


@dataclass
class Tolerances:
    text_levenshtein_pct: float = 0.5
    metadata_date_seconds: int = 1


def load_tolerances() -> Tolerances:
    if not MANIFEST_PATH.is_file():
        return Tolerances()
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        m = yaml.safe_load(f) or {}
    t = m.get("tolerances") or {}
    return Tolerances(
        text_levenshtein_pct=float(t.get("text_levenshtein_pct", 0.5)),
        metadata_date_seconds=int(t.get("metadata_date_seconds", 1)),
    )


def canonicalize_text(s: str) -> str:
    """Apply the same normalization rules implementations must apply to content.text."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in s.split("\n")]
    s = "\n".join(lines)
    # Collapse 3+ blank lines to 2 (i.e. one blank line between paragraphs).
    while "\n\n\n" in s:
        s = s.replace("\n\n\n", "\n\n")
    return s.strip()


def compare_text(actual: str, expected: str, tol: Tolerances, path: str) -> list[str]:
    a = canonicalize_text(actual or "")
    e = canonicalize_text(expected or "")
    if a == e:
        return []
    dist = levenshtein(a, e)
    pct = (dist / max(1, len(e))) * 100
    if pct <= tol.text_levenshtein_pct:
        return []
    return [
        f"{path}: text drift {pct:.3f}% > tolerance {tol.text_levenshtein_pct}% "
        f"({dist} edits over {len(e)} chars)"
    ]


def compare_datetime(actual: Any, expected: Any, tol: Tolerances, path: str) -> list[str]:
    if actual == expected:
        return []
    if actual is None or expected is None:
        return [f"{path}: presence mismatch (actual={actual!r}, expected={expected!r})"]
    try:
        da = datetime.fromisoformat(str(actual).replace("Z", "+00:00"))
        de = datetime.fromisoformat(str(expected).replace("Z", "+00:00"))
    except ValueError as exc:
        return [f"{path}: unparseable datetime ({exc})"]
    delta = abs((da - de).total_seconds())
    if delta > tol.metadata_date_seconds:
        return [f"{path}: {delta:.1f}s drift > tolerance {tol.metadata_date_seconds}s"]
    return []


def compare(actual: dict, expected: dict, tol: Tolerances) -> list[str]:
    diffs: list[str] = []

    # source
    for k in ("mime_type", "sha256", "size_bytes"):
        a = actual.get("source", {}).get(k)
        e = expected.get("source", {}).get(k)
        if a != e:
            diffs.append(f"/source/{k}: actual={a!r} expected={e!r}")

    # metadata
    ma = actual.get("metadata", {}) or {}
    me = expected.get("metadata", {}) or {}
    for k in ("title", "author", "language", "page_count", "word_count"):
        if ma.get(k) != me.get(k):
            diffs.append(f"/metadata/{k}: actual={ma.get(k)!r} expected={me.get(k)!r}")
    for k in ("created", "modified"):
        diffs.extend(compare_datetime(ma.get(k), me.get(k), tol, f"/metadata/{k}"))

    extra_a = ma.get("extra") or {}
    extra_e = me.get("extra") or {}
    for k, v_e in extra_e.items():
        if k in extra_a and extra_a[k] != v_e:
            diffs.append(f"/metadata/extra/{k}: actual={extra_a[k]!r} expected={v_e!r}")
        # Missing keys in actual are tolerated (impl may not extract that namespace).
    for k in extra_a:
        if k not in extra_e:
            diffs.append(f"/metadata/extra/{k}: unknown extra key (not in expected)")

    # content
    ca = actual.get("content", {}) or {}
    ce = expected.get("content", {}) or {}
    diffs.extend(compare_text(ca.get("text", ""), ce.get("text", ""), tol, "/content/text"))

    pages_a = ca.get("pages")
    pages_e = ce.get("pages")
    if pages_e is not None:
        if pages_a is None:
            diffs.append("/content/pages: actual is null, expected is array")
        elif len(pages_a) != len(pages_e):
            diffs.append(
                f"/content/pages: actual length {len(pages_a)} != expected {len(pages_e)}"
            )
        else:
            for i, (pa, pe) in enumerate(zip(pages_a, pages_e)):
                diffs.extend(
                    compare_text(pa.get("text", ""), pe.get("text", ""), tol, f"/content/pages/{i}/text")
                )

    # warnings — set-equality with prefix-fuzzy match.
    wa = set(actual.get("warnings") or [])
    we = set(expected.get("warnings") or [])
    for w in we:
        if w not in wa and not any(a.startswith(w.split(":")[0]) for a in wa):
            diffs.append(f"/warnings: missing expected warning {w!r}")

    return diffs


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: diff_extraction.py <actual.json> <expected.json|fixture-path>",
            file=sys.stderr,
        )
        return 2

    actual_path = Path(argv[1])
    second = Path(argv[2])

    if not actual_path.is_file():
        print(f"ERROR: {actual_path} not found.", file=sys.stderr)
        return 2

    # If second is a fixture path (not a .json), locate its sibling .expected.json.
    if second.suffix != ".json":
        candidate = second.with_suffix(second.suffix + ".expected.json")
        if not candidate.is_file():
            candidate = second.with_suffix(".expected.json")
        if not candidate.is_file():
            print(
                f"ERROR: cannot locate .expected.json for fixture {second}.",
                file=sys.stderr,
            )
            return 2
        expected_path = candidate
    else:
        expected_path = second

    if not expected_path.is_file():
        print(f"ERROR: {expected_path} not found.", file=sys.stderr)
        return 2

    actual = json.loads(actual_path.read_text(encoding="utf-8"))
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    tol = load_tolerances()

    diffs = compare(actual, expected, tol)
    if not diffs:
        print(f"OK: {actual_path.name} matches {expected_path.name} within tolerance.")
        return 0

    print(f"DIFF ({len(diffs)} material difference(s)):", file=sys.stderr)
    for d in diffs:
        print(f"  - {d}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
