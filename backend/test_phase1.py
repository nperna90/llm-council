"""
Phase 1 verification tests.
Run with: uv run python backend/test_phase1.py
"""
import asyncio
import sys
from pathlib import Path

# Ensure project root is on path when run as script
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


def ok(name: str, cond: bool, detail: str = "") -> None:
    sym = "✅" if cond else "❌"
    msg = f"  {sym} {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if not cond:
        sys.exit(1)


def run_import_checks() -> None:
    print("\n--- Import checks ---")
    try:
        from backend.utils import extract_json, safe_parse_float
        ok("backend.utils: extract_json, safe_parse_float", True)
    except Exception as e:
        ok("backend.utils", False, str(e))

    try:
        from backend.config import AGENT_MODELS, RISK_PROFILES
        ok("backend.config: AGENT_MODELS, RISK_PROFILES", True)
    except Exception as e:
        ok("backend.config", False, str(e))

    try:
        from backend.council import build_conversation_context
        ok("backend.council: build_conversation_context", True)
    except Exception as e:
        ok("backend.council", False, str(e))


def run_extract_json_tests() -> None:
    print("\n--- extract_json ---")
    from backend.utils import extract_json

    # Clean JSON string
    out = extract_json('{"a": 1, "b": "x"}')
    ok("Clean JSON", isinstance(out, dict) and out.get("a") == 1 and out.get("b") == "x")

    # JSON in markdown fences
    text = "```json\n{\"x\": 42}\n```"
    out = extract_json(text)
    ok("JSON in ```json fences", isinstance(out, dict) and out.get("x") == 42)

    # Preamble + JSON block
    text = "Here is the result:\n\n{\"key\": \"value\"}"
    out = extract_json(text)
    ok("Preamble + {...}", isinstance(out, dict) and out.get("key") == "value")

    # Invalid JSON -> error dict
    out = extract_json("not json at all { incomplete")
    ok("Invalid JSON returns error dict", "error" in out and "raw_text" in out)


def run_build_conversation_context_tests() -> None:
    print("\n--- build_conversation_context ---")
    from backend.council import build_conversation_context

    out = build_conversation_context([])
    ok("Empty history → empty string", out == "")

    # 6 messages = 3 user+assistant pairs; max_turns=3 → all 3 returned
    history = [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "stage3": {"response": "First answer"}},
        {"role": "user", "content": "Second question"},
        {"role": "assistant", "stage3": {"response": "Second answer"}},
        {"role": "user", "content": "Third question"},
        {"role": "assistant", "stage3": {"response": "Third answer"}},
    ]
    out = build_conversation_context(history, max_turns=3)
    has_header = "=== CONVERSATION CONTEXT ===" in out
    has_three_pairs = out.count("User:") == 3 and out.count("Assistant:") == 3
    has_first = "First question" in out and "First answer" in out
    has_third = "Third question" in out and "Third answer" in out
    ok("6 messages → 3 pairs (last 3)", has_header and has_three_pairs and has_first and has_third)


def run_config_tests() -> None:
    print("\n--- Config: AGENT_MODELS & RISK_PROFILES ---")
    from backend.config import AGENT_MODELS, RISK_PROFILES

    expected_agents = {
        "quant", "risk", "macro", "fundamental", "sentiment",
        "contrarian", "chairman", "reviewer", "planner",
    }
    missing = expected_agents - set(AGENT_MODELS.keys())
    ok("AGENT_MODELS has all expected keys", len(missing) == 0, f"missing: {missing}" if missing else "")

    expected_risk = {"conservative", "moderate", "aggressive"}
    missing_risk = expected_risk - set(RISK_PROFILES.keys())
    ok("RISK_PROFILES has all expected keys", len(missing_risk) == 0, f"missing: {missing_risk}" if missing_risk else "")

    for name, profile in RISK_PROFILES.items():
        ok(f"  RISK_PROFILES[{name}] has max_position_pct, max_risk_score",
           "max_position_pct" in profile and "max_risk_score" in profile)


async def run_generate_title_test() -> None:
    print("\n--- generate_title ---")
    from backend.main import generate_title

    query = "What about $NVDA for a 6-month hold?"
    title = await generate_title(query)
    # Should return non-empty; if SIMULATION_MODE we get mock title, else possibly fallback (first 50 chars)
    is_non_empty = isinstance(title, str) and len(title) > 0
    ok("generate_title returns non-empty string", is_non_empty, f"got: {title[:50]!r}...")
    # Fallback is query[:50]; API/mock can return up to 80 chars
    ok("generate_title length reasonable", len(title) <= 80 or title == query[:50], f"len={len(title)}")


def main() -> None:
    print("Phase 1 tests")
    run_import_checks()
    run_extract_json_tests()
    run_build_conversation_context_tests()
    run_config_tests()
    asyncio.run(run_generate_title_test())
    print("\n✅ All Phase 1 tests passed.\n")


if __name__ == "__main__":
    main()
