#!/usr/bin/env python3
"""
tests-summary: Generate Markdown summaries from test and coverage reports.

Supported report formats
------------------------
Coverage:
    * LCOV          --lcov PATH          (default: lcov.info)

Test results:
    * JUnit XML     --junit PATH         (default: junit.xml)
    * pytest-json   --pytest-json PATH   (default: .report.json)

Each source is optional. A file is silently skipped when it does not exist,
so the script integrates cleanly into CI pipelines that may or may not produce
every report type.

Usage:
    python main.py [--lcov PATH] [--junit PATH] [--pytest-json PATH]
        [--summary-out PATH] [--comment-out PATH] [--run-url URL]
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# Data models
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class FileRecord:
    """Coverage data for a single source file."""

    path: str
    lines_found: int = 0
    lines_hit: int = 0
    branches_found: int = 0
    branches_hit: int = 0
    functions_found: int = 0
    functions_hit: int = 0

    @property
    def line_pct(self) -> float:
        return (self.lines_hit / self.lines_found * 100) if self.lines_found else 100.0

    @property
    def branch_pct(self) -> float:
        return (self.branches_hit / self.branches_found * 100) if self.branches_found else 100.0

    @property
    def fn_pct(self) -> float:
        return (self.functions_hit / self.functions_found * 100) if self.functions_found else 100.0


@dataclass
class CoverageSummary:
    """Aggregated coverage data across all source files."""

    files: list[FileRecord] = field(default_factory=list)
    source: str = ""

    @property
    def total(self) -> FileRecord:
        t = FileRecord(path="TOTAL")
        for r in self.files:
            t.lines_found += r.lines_found
            t.lines_hit += r.lines_hit
            t.branches_found += r.branches_found
            t.branches_hit += r.branches_hit
            t.functions_found += r.functions_found
            t.functions_hit += r.functions_hit
        return t


@dataclass
class TestCase:
    """A single test case result."""

    name: str
    classname: str = ""
    status: str = "passed"  # passed | failed | skipped | error
    duration: float = 0.0
    message: str = ""


@dataclass
class TestSuite:
    """A named collection of test cases (maps to a JUnit <testsuite>)."""

    name: str
    test_cases: list[TestCase] = field(default_factory=list)
    duration: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for t in self.test_cases if t.status == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for t in self.test_cases if t.status == "failed")

    @property
    def skipped(self) -> int:
        return sum(1 for t in self.test_cases if t.status == "skipped")

    @property
    def errors(self) -> int:
        return sum(1 for t in self.test_cases if t.status == "error")

    @property
    def total(self) -> int:
        return len(self.test_cases)


@dataclass
class TestResults:
    """Aggregated test results across all suites."""

    suites: list[TestSuite] = field(default_factory=list)
    source: str = ""
    duration: float = 0.0

    @property
    def passed(self) -> int:
        return sum(s.passed for s in self.suites)

    @property
    def failed(self) -> int:
        return sum(s.failed for s in self.suites)

    @property
    def skipped(self) -> int:
        return sum(s.skipped for s in self.suites)

    @property
    def errors(self) -> int:
        return sum(s.errors for s in self.suites)

    @property
    def total(self) -> int:
        return sum(s.total for s in self.suites)

    @property
    def all_test_cases(self) -> list[TestCase]:
        cases: list[TestCase] = []
        for suite in self.suites:
            cases.extend(suite.test_cases)
        return cases


# ══════════════════════════════════════════════════════════════════════════════
# Parser base classes  (extend these to add new report formats)
# ══════════════════════════════════════════════════════════════════════════════


class CoverageParser(ABC):
    """Base class for all coverage-report parsers."""

    @abstractmethod
    def parse(self, path: Path) -> CoverageSummary:
        """Parse *path* and return a :class:`CoverageSummary`."""


class TestResultsParser(ABC):
    """Base class for all test-results parsers."""

    @abstractmethod
    def parse(self, path: Path) -> TestResults:
        """Parse *path* and return a :class:`TestResults`."""


# ══════════════════════════════════════════════════════════════════════════════
# Coverage parsers
# ══════════════════════════════════════════════════════════════════════════════


class LcovParser(CoverageParser):
    """Parse an LCOV ``lcov.info`` coverage report."""

    def parse(self, path: Path) -> CoverageSummary:
        files: list[FileRecord] = []
        current: FileRecord | None = None

        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("SF:"):
                current = FileRecord(path=line[3:])
            elif line == "end_of_record":
                if current is not None:
                    files.append(current)
                    current = None
            elif current is not None:
                if line.startswith("LF:"):
                    current.lines_found = int(line[3:])
                elif line.startswith("LH:"):
                    current.lines_hit = int(line[3:])
                elif line.startswith("BRF:"):
                    current.branches_found = int(line[4:])
                elif line.startswith("BRH:"):
                    current.branches_hit = int(line[4:])
                elif line.startswith("FNF:"):
                    current.functions_found = int(line[4:])
                elif line.startswith("FNH:"):
                    current.functions_hit = int(line[4:])

        return CoverageSummary(files=files, source="lcov")


# ══════════════════════════════════════════════════════════════════════════════
# Test-results parsers
# ══════════════════════════════════════════════════════════════════════════════


class JunitParser(TestResultsParser):
    """Parse a JUnit XML report.

    Handles both ``<testsuites>`` (multi-suite) and bare ``<testsuite>``
    (single-suite) root elements, as produced by pytest, Maven, Gradle, etc.
    """

    def parse(self, path: Path) -> TestResults:
        tree = ET.parse(str(path))
        root = tree.getroot()

        if root.tag == "testsuites":
            suite_elements = root.findall("testsuite")
        elif root.tag == "testsuite":
            suite_elements = [root]
        else:
            raise ValueError(
                f"Unexpected JUnit XML root element: <{root.tag}>")

        suites: list[TestSuite] = []
        total_duration = 0.0

        for suite_el in suite_elements:
            name = suite_el.get("name", "unnamed")
            duration = float(suite_el.get("time", 0) or 0)
            total_duration += duration
            cases: list[TestCase] = []

            for tc_el in suite_el.findall("testcase"):
                tc_name = tc_el.get("name", "?")
                classname = tc_el.get("classname", "")
                tc_duration = float(tc_el.get("time", 0) or 0)

                failure_el = tc_el.find("failure")
                error_el = tc_el.find("error")
                skipped_el = tc_el.find("skipped")

                if failure_el is not None:
                    status = "failed"
                    message = failure_el.get("message", "") or (
                        failure_el.text or "")
                elif error_el is not None:
                    status = "error"
                    message = error_el.get("message", "") or (
                        error_el.text or "")
                elif skipped_el is not None:
                    status = "skipped"
                    message = skipped_el.get("message", "") or (
                        skipped_el.text or "")
                else:
                    status = "passed"
                    message = ""

                cases.append(
                    TestCase(
                        name=tc_name,
                        classname=classname,
                        status=status,
                        duration=tc_duration,
                        message=message.strip() if message else "",
                    )
                )

            suites.append(
                TestSuite(name=name, test_cases=cases, duration=duration))

        return TestResults(suites=suites, source="junit", duration=total_duration)


class PytestJsonParser(TestResultsParser):
    """Parse a ``pytest-json-report`` JSON report.

    See: https://github.com/numirias/pytest-json-report
    """

    # Map pytest outcome strings to our canonical status values.
    _OUTCOME_MAP: dict[str, str] = {
        "passed": "passed",
        "failed": "failed",
        "skipped": "skipped",
        "xfailed": "skipped",
        "xpassed": "passed",
        "error": "error",
    }

    def parse(self, path: Path) -> TestResults:
        data = json.loads(path.read_text(encoding="utf-8"))
        duration = float(data.get("duration", 0))
        raw_tests: list[dict] = data.get("tests", [])

        # Group test cases by their module (the part before the first "::").
        suites: dict[str, TestSuite] = {}

        for test in raw_tests:
            nodeid: str = test.get("nodeid", "?")
            if "::" in nodeid:
                module, test_name = nodeid.split("::", 1)
            else:
                module, test_name = nodeid, nodeid

            outcome = test.get("outcome", "passed")
            status = self._OUTCOME_MAP.get(outcome, outcome)

            # Prefer the duration of the "call" phase; fall back to "setup".
            tc_duration = 0.0
            for phase in ("call", "setup"):
                if phase in test:
                    tc_duration = float(test[phase].get("duration", 0))
                    break

            # Extract a human-readable failure/skip message.
            message = self._extract_message(test, outcome)

            if module not in suites:
                suites[module] = TestSuite(name=module)

            suites[module].test_cases.append(
                TestCase(name=test_name, classname=module,
                         status=status, duration=tc_duration, message=message)
            )

        # Recalculate per-suite durations from individual test cases.
        for suite in suites.values():
            suite.duration = sum(tc.duration for tc in suite.test_cases)

        return TestResults(suites=list(suites.values()), source="pytest-json", duration=duration)

    @staticmethod
    def _extract_message(test: dict, outcome: str) -> str:
        """Return a short, single-line message for a failed or skipped test."""
        for phase in ("call", "setup", "teardown"):
            if phase not in test:
                continue
            phase_outcome = test[phase].get("outcome", "")
            if phase_outcome in ("failed", "error") or (phase_outcome == "skipped" and outcome == "skipped"):
                longrepr = test[phase].get("longrepr", "")
                if isinstance(longrepr, str) and longrepr:
                    # Return just the first meaningful line, capped at 200 chars.
                    return longrepr.splitlines()[0][:200]
                if isinstance(longrepr, list) and longrepr:
                    return str(longrepr[-1])[:200]
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# Shared formatting helpers
# ══════════════════════════════════════════════════════════════════════════════


def _status_icon(pct: float) -> str:
    if pct >= 90:
        return "🟢"
    if pct >= 70:
        return "🟡"
    return "🔴"


def _result_icon(results: TestResults) -> str:
    if results.failed > 0 or results.errors > 0:
        return "❌"
    if results.skipped > 0:
        return "⚠️"
    return "✅"


def _fmt_pct(pct: float) -> str:
    return f"{pct:.1f}%"


def _duration_str(seconds: float) -> str:
    if seconds < 0.001:
        return "< 1ms"
    if seconds < 1.0:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60.0:
        return f"{seconds:.2f}s"
    m, s = divmod(seconds, 60)
    return f"{int(m)}m {s:.0f}s"


def _short_path(path: str) -> str:
    """Strip common leading path segments for readability."""
    for prefix in ("app/aqueduct/", "app/", "src/"):
        if path.startswith(prefix):
            return path[len(prefix):]
    return path


def _write_output(content: str, dest: str) -> None:
    if dest == "-":
        print(content, end="")
    else:
        out = Path(dest)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# Test-results formatters
# ══════════════════════════════════════════════════════════════════════════════

_SOURCE_LABELS: dict[str, str] = {
    "junit": "JUnit XML", "pytest-json": "pytest JSON report", "lcov": "LCOV"}


def format_test_results_summary(results: TestResults) -> str:
    icon = _result_icon(results)
    label = _SOURCE_LABELS.get(results.source, results.source)

    lines = [
        f"## {icon} Test Results",
        "",
        f"*Source: {label}*",
        "",
        "| ✅ Passed | ❌ Failed | ⚠️ Skipped | 🔥 Errors | Total | Duration |",
        "|----------:|---------:|----------:|----------:|------:|---------:|",
        (
            f"| {results.passed}"
            f" | {results.failed}"
            f" | {results.skipped}"
            f" | {results.errors}"
            f" | {results.total}"
            f" | {_duration_str(results.duration)} |"
        ),
        "",
    ]

    # Prominently list any failed/errored tests.
    failed = [tc for tc in results.all_test_cases if tc.status in (
        "failed", "error")]
    if failed:
        lines += ["### Failed Tests", ""]
        for tc in failed[:20]:
            label_str = f"{tc.classname}::{tc.name}" if tc.classname else tc.name
            lines.append(f"- ❌ `{label_str}`")
            if tc.message:
                first_line = tc.message.splitlines()[0][:120]
                lines.append(f"  > {first_line}")
        if len(failed) > 20:
            lines.append(f"- *…and {len(failed) - 20} more*")
        lines.append("")

    # Per-suite breakdown (only meaningful when there is more than one suite).
    if len(results.suites) > 1:
        lines += [
            "<details>",
            "<summary>Per-suite breakdown</summary>",
            "",
            "| Suite | Passed | Failed | Skipped | Errors | Total | Duration |",
            "|-------|-------:|-------:|--------:|-------:|------:|---------:|",
        ]
        for suite in sorted(results.suites, key=lambda s: s.name):
            lines.append(
                f"| `{suite.name}`"
                f" | {suite.passed}"
                f" | {suite.failed}"
                f" | {suite.skipped}"
                f" | {suite.errors}"
                f" | {suite.total}"
                f" | {_duration_str(suite.duration)} |"
            )
        lines += ["", "</details>", ""]

    return "\n".join(lines)


def format_test_results_comment(results: TestResults, run_url: str = "") -> str:
    icon = _result_icon(results)
    detail_link = f" · [Details →]({run_url})" if run_url else ""

    lines = [
        f"<!-- test-results-{results.source} -->",
        f"## {icon} Test Results{detail_link}",
        "",
        "| ✅ Passed | ❌ Failed | ⚠️ Skipped | Total |",
        "|----------:|---------:|----------:|------:|",
        f"| {results.passed} | {results.failed} | {results.skipped} | {results.total} |",
        "",
    ]

    failed = [tc for tc in results.all_test_cases if tc.status in (
        "failed", "error")]
    if failed:
        lines += ["<details>", "<summary>Failed tests</summary>", ""]
        for tc in failed[:10]:
            label = f"{tc.classname}::{tc.name}" if tc.classname else tc.name
            lines.append(f"- `{label}`")
        if len(failed) > 10:
            lines.append(f"- *…and {len(failed) - 10} more*")
        lines += ["", "</details>", ""]

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Coverage formatters
# ══════════════════════════════════════════════════════════════════════════════


def format_coverage_summary(summary: CoverageSummary) -> str:
    total = summary.total
    label = _SOURCE_LABELS.get(summary.source, summary.source)

    lines = [
        "## Coverage Report",
        "",
        f"*Source: {label}*",
        "",
        "### Overall",
        "",
        "| Metric | Hit | Total | % |",
        "|--------|----:|------:|--:|",
        f"| Lines | {total.lines_hit} | {total.lines_found} | {_status_icon(total.line_pct)} **{_fmt_pct(total.line_pct)}** |",
        f"| Branches | {total.branches_hit} | {total.branches_found} | {_status_icon(total.branch_pct)} **{_fmt_pct(total.branch_pct)}** |",
        f"| Functions | {total.functions_hit} | {total.functions_found} | {_status_icon(total.fn_pct)} **{_fmt_pct(total.fn_pct)}** |",
        "",
        "<details>",
        "<summary>Per-file breakdown</summary>",
        "",
        "| File | Lines | Branches | Functions |",
        "|------|------:|---------:|----------:|",
    ]

    for r in sorted(summary.files, key=lambda x: x.line_pct):
        name = _short_path(r.path)
        lines.append(
            f"| `{name}`"
            f" | {_status_icon(r.line_pct)} {_fmt_pct(r.line_pct)} `{r.lines_hit}/{r.lines_found}`"
            f" | {_status_icon(r.branch_pct)} {_fmt_pct(r.branch_pct)} `{r.branches_hit}/{r.branches_found}`"
            f" | {_status_icon(r.fn_pct)} {_fmt_pct(r.fn_pct)} `{r.functions_hit}/{r.functions_found}` |"
        )

    lines += ["", "</details>", ""]
    return "\n".join(lines)


def format_coverage_comment(summary: CoverageSummary, run_url: str = "") -> str:
    total = summary.total
    detail_link = f" · [Full report →]({run_url})" if run_url else ""
    worst = sorted(summary.files, key=lambda x: x.line_pct)[:5]

    lines = [
        "<!-- coverage-report -->",
        f"## {_status_icon(total.line_pct)} Coverage Summary{detail_link}",
        "",
        "| Lines | Branches | Functions |",
        "|------:|---------:|----------:|",
        (
            f"| {_status_icon(total.line_pct)} **{_fmt_pct(total.line_pct)}**"
            f" `{total.lines_hit}/{total.lines_found}`"
            f" | {_status_icon(total.branch_pct)} **{_fmt_pct(total.branch_pct)}**"
            f" `{total.branches_hit}/{total.branches_found}`"
            f" | {_status_icon(total.fn_pct)} **{_fmt_pct(total.fn_pct)}**"
            f" `{total.functions_hit}/{total.functions_found}` |"
        ),
        "",
        "<details>",
        "<summary>Lowest coverage files</summary>",
        "",
        "| File | Lines | Branches |",
        "|------|------:|---------:|",
    ]

    for r in worst:
        name = _short_path(r.path)
        lines.append(
            f"| `{name}`"
            f" | {_status_icon(r.line_pct)} {_fmt_pct(r.line_pct)}"
            f" | {_status_icon(r.branch_pct)} {_fmt_pct(r.branch_pct)} |"
        )

    lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


# ══════════════════════════════════════════════════════════════════════════════
# Parser / formatter registry
#
# To add a new report format:
#   1. Implement a subclass of CoverageParser or TestResultsParser.
#   2. Add an entry to COVERAGE_SOURCES or TEST_SOURCES below.
#   3. Add the corresponding --<name> / --no-<name> arguments in main().
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class CoverageSource:
    name: str
    default_path: str
    parser: CoverageParser
    summary_formatter: object  # Callable[[CoverageSummary], str]
    comment_formatter: object  # Callable[[CoverageSummary, str], str]


@dataclass
class TestSource:
    name: str
    default_path: str
    parser: TestResultsParser
    summary_formatter: object  # Callable[[TestResults], str]
    comment_formatter: object  # Callable[[TestResults, str], str]


COVERAGE_SOURCES: list[CoverageSource] = [
    CoverageSource(
        name="lcov",
        default_path="lcov.info",
        parser=LcovParser(),
        summary_formatter=format_coverage_summary,
        comment_formatter=format_coverage_comment,
    )
]

TEST_SOURCES: list[TestSource] = [
    TestSource(
        name="junit",
        default_path="junit.xml",
        parser=JunitParser(),
        summary_formatter=format_test_results_summary,
        comment_formatter=format_test_results_comment,
    ),
    TestSource(
        name="pytest-json",
        default_path=".report.json",
        parser=PytestJsonParser(),
        summary_formatter=format_test_results_summary,
        comment_formatter=format_test_results_comment,
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Markdown summaries from test and coverage reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Each report source is optional.  A file is silently skipped when it does not
exist, so you only need to supply the flags that apply to your project.

Examples:
    # Use all defaults (looks for lcov.info, junit.xml, .report.json):
    python main.py --summary-out "$GITHUB_STEP_SUMMARY"

    # Explicit paths + PR comment output:
    python main.py \\
        --lcov reports/coverage/lcov.info \\
        --junit reports/test/junit.xml \\
        --summary-out reports/step-summary.md \\
        --comment-out reports/pr-comment.md \\
        --run-url "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"

    # Coverage only, no test results:
    python main.py --no-junit --no-pytest-json --lcov coverage/lcov.info
""",
    )

    cov = parser.add_argument_group("Coverage sources")
    cov.add_argument(
        "--lcov", default="lcov.info", metavar="PATH", help="Path to LCOV coverage file (default: lcov.info)"
    )
    cov.add_argument("--no-lcov", action="store_true",
                     help="Disable LCOV coverage report")

    tst = parser.add_argument_group("Test result sources")
    tst.add_argument(
        "--junit", default="junit.xml", metavar="PATH", help="Path to JUnit XML report (default: junit.xml)"
    )
    tst.add_argument("--no-junit", action="store_true",
                     help="Disable JUnit XML test results")
    tst.add_argument(
        "--pytest-json",
        default=".report.json",
        metavar="PATH",
        help="Path to pytest-json-report file (default: .report.json)",
    )
    tst.add_argument("--no-pytest-json", action="store_true",
                     help="Disable pytest-json-report test results")

    out = parser.add_argument_group("Output options")
    out.add_argument(
        "--summary-out",
        default="-",
        metavar="PATH",
        help="Output path for the detailed step-summary Markdown (- for stdout)",
    )
    out.add_argument(
        "--comment-out", default=None, metavar="PATH", help="Output path for the brief PR-comment Markdown"
    )
    out.add_argument(
        "--run-url",
        default="",
        metavar="URL",
        help="GitHub Actions run URL to embed as a hyperlink in PR comment output",
    )

    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()

    summary_sections: list[str] = []
    comment_sections: list[str] = []
    found_any = False

    # ── Test-results sources (listed before coverage in the output) ──────────

    for src in TEST_SOURCES:
        # Map source name to the CLI flag value (hyphens → underscores for getattr).
        flag_attr = src.name.replace("-", "_")
        no_flag_attr = f"no_{flag_attr}"
        path_str: str = getattr(args, flag_attr)
        disabled: bool = getattr(args, no_flag_attr)

        if disabled:
            continue

        report_path = Path(path_str)
        if not report_path.exists():
            continue

        try:
            results = src.parser.parse(report_path)
            summary_sections.append(src.summary_formatter(
                results))  # type: ignore[call-arg]
            comment_sections.append(src.comment_formatter(
                results, args.run_url))  # type: ignore[call-arg]
            found_any = True
        except Exception as exc:  # noqa: BLE001
            print(
                f"warning: failed to parse {src.name} report at {report_path}: {exc}", file=sys.stderr)

    # ── Coverage sources ─────────────────────────────────────────────────────

    for src in COVERAGE_SOURCES:
        flag_attr = src.name.replace("-", "_")
        no_flag_attr = f"no_{flag_attr}"
        path_str = getattr(args, flag_attr)
        disabled = getattr(args, no_flag_attr)

        if disabled:
            continue

        report_path = Path(path_str)
        if not report_path.exists():
            continue

        try:
            coverage = src.parser.parse(report_path)
            if not coverage.files:
                print(
                    f"warning: no coverage records found in {report_path}", file=sys.stderr)
                continue
            summary_sections.append(src.summary_formatter(
                coverage))  # type: ignore[call-arg]
            comment_sections.append(src.comment_formatter(
                coverage, args.run_url))  # type: ignore[call-arg]
            found_any = True
        except Exception as exc:  # noqa: BLE001
            print(
                f"warning: failed to parse {src.name} report at {report_path}: {exc}", file=sys.stderr)

    if not found_any:
        print(
            "warning: no report files found — nothing to output.\n" "Run with --help to see available options.",
            file=sys.stderr,
        )
        return 1

    separator = "\n---\n\n"
    _write_output(separator.join(summary_sections) + "\n", args.summary_out)

    if args.comment_out:
        _write_output("\n\n".join(comment_sections) + "\n", args.comment_out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
