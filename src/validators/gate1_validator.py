"""Gate 1 Validator — Structural integrity checks.

6 checks:
1. Valid JSON (Pydantic model validates)
2. Required fields present
3. Correct types
4. No placeholder content
5. Trace complete
6. Count matches array length
"""

from __future__ import annotations

from typing import Any, Union

from models.schemas import (
    CampaignCraftOutput,
    EnrichmentOutput,
    ReconOutput,
    SegmentationOutput,
    ValidationResult,
)

PLACEHOLDER_MARKERS = ["TBD", "TODO", "PLACEHOLDER", "FIXME", "XXX"]

OutputType = Union[ReconOutput, EnrichmentOutput, SegmentationOutput, CampaignCraftOutput]


def _check_no_placeholders(data: dict[str, Any], path: str = "") -> list[str]:
    """Recursively check for placeholder values in a dict."""
    failures: list[str] = []
    for key, value in data.items():
        full_path = f"{path}.{key}" if path else key
        if isinstance(value, str):
            for marker in PLACEHOLDER_MARKERS:
                if marker in value.upper():
                    failures.append(f"Placeholder found at {full_path}: '{value}'")
        elif isinstance(value, dict):
            failures.extend(_check_no_placeholders(value, full_path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    failures.extend(_check_no_placeholders(item, f"{full_path}[{i}]"))
                elif isinstance(item, str):
                    for marker in PLACEHOLDER_MARKERS:
                        if marker in item.upper():
                            failures.append(f"Placeholder found at {full_path}[{i}]: '{item}'")
    return failures


def validate_gate1(output: OutputType) -> ValidationResult:
    """Run Gate 1 structural checks on any agent output."""
    failures: list[str] = []
    checks_run = 0
    checks_passed = 0

    # Check 1: Valid JSON / Pydantic model
    checks_run += 1
    try:
        data = output.model_dump(by_alias=True)
        checks_passed += 1
    except Exception as e:
        failures.append(f"Check 1 (valid JSON): Model serialization failed: {e}")
        return ValidationResult(
            gate="gate1",
            passed=False,
            checksRun=checks_run,
            checksPassed=checks_passed,
            failures=failures,
        )

    # Check 2: Required fields present
    checks_run += 1
    required_top = ["taskId", "agent", "timestamp"]
    missing = [f for f in required_top if not data.get(f)]
    if missing:
        failures.append(f"Check 2 (required fields): Missing top-level fields: {missing}")
    else:
        checks_passed += 1

    # Check 3: Correct types
    checks_run += 1
    type_errors: list[str] = []
    if not isinstance(data.get("taskId"), str):
        type_errors.append("taskId must be string")
    if not isinstance(data.get("agent"), str):
        type_errors.append("agent must be string")
    if not isinstance(data.get("timestamp"), str):
        type_errors.append("timestamp must be string")
    if type_errors:
        failures.append(f"Check 3 (types): {', '.join(type_errors)}")
    else:
        checks_passed += 1

    # Check 4: No placeholders
    checks_run += 1
    placeholder_issues = _check_no_placeholders(data)
    if placeholder_issues:
        failures.append(f"Check 4 (no placeholders): {'; '.join(placeholder_issues[:3])}")
    else:
        checks_passed += 1

    # Check 5: Trace complete
    checks_run += 1
    trace = data.get("trace", {})
    if not trace:
        failures.append("Check 5 (trace): Trace object is missing or empty")
    elif not trace.get("vaultFilesUsed"):
        failures.append("Check 5 (trace): vaultFilesUsed is empty")
    else:
        checks_passed += 1

    # Check 6: Count matches array length
    checks_run += 1
    count = data.get("count", -1)
    # Campaign Craft uses "drafts", others use "records"
    items = data.get("records") or data.get("drafts") or []
    if count != len(items):
        failures.append(
            f"Check 6 (count): count={count} but array has {len(items)} items"
        )
    else:
        checks_passed += 1

    return ValidationResult(
        gate="gate1",
        passed=len(failures) == 0,
        checksRun=checks_run,
        checksPassed=checks_passed,
        failures=failures,
    )
