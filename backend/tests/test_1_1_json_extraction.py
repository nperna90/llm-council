"""
Test: backend/utils.py — extract_json and safe_parse_float
Run AFTER completing Task 1.1
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.tests.conftest import TestResult

def test_json_extraction():
    from backend.utils import extract_json, safe_parse_float
    
    t = TestResult()
    
    # --- Test 1: Clean JSON ---
    result = extract_json('{"sentiment": "BULLISH", "confidence": 85}')
    t.check(
        "Clean JSON parses correctly",
        result.get("sentiment") == "BULLISH" and result.get("confidence") == 85,
        f"Got: {result}"
    )
    
    # --- Test 2: JSON in markdown fences ---
    fenced = '```json\n{"sentiment": "BEARISH", "confidence": 42}\n```'
    result = extract_json(fenced)
    t.check(
        "Fenced JSON parses correctly",
        result.get("sentiment") == "BEARISH" and result.get("confidence") == 42,
        f"Got: {result}"
    )
    
    # --- Test 3: JSON with preamble text ---
    preamble = 'Here is my analysis:\n\n{"sentiment": "NEUTRAL", "confidence": 60}'
    result = extract_json(preamble)
    t.check(
        "JSON with preamble text parses correctly",
        result.get("sentiment") == "NEUTRAL",
        f"Got: {result}"
    )
    
    # --- Test 4: JSON with trailing text ---
    trailing = '{"sentiment": "BULLISH", "confidence": 90}\n\nI hope this helps!'
    result = extract_json(trailing)
    t.check(
        "JSON with trailing text parses correctly",
        result.get("sentiment") == "BULLISH",
        f"Got: {result}"
    )
    
    # --- Test 5: Completely invalid input ---
    result = extract_json("This is not JSON at all, just random text")
    t.check(
        "Invalid input returns error dict",
        "error" in result,
        f"Expected 'error' key, got: {result}"
    )
    
    # --- Test 6: Empty string ---
    result = extract_json("")
    t.check(
        "Empty string returns error dict",
        "error" in result,
        f"Got: {result}"
    )
    
    # --- Test 7: Nested JSON ---
    nested = '{"agent": "quant", "technical": {"trend": "UPTREND", "rsi": 65.3}}'
    result = extract_json(nested)
    t.check(
        "Nested JSON parses correctly",
        result.get("technical", {}).get("trend") == "UPTREND",
        f"Got: {result}"
    )
    
    # --- Test 8: JSON with code fence but no json label ---
    bare_fence = '```\n{"key": "value"}\n```'
    result = extract_json(bare_fence)
    t.check(
        "Bare code fence (no json label) parses correctly",
        result.get("key") == "value",
        f"Got: {result}"
    )
    
    # --- Test 9: Schema validation (if Pydantic available) ---
    try:
        from pydantic import BaseModel
        
        class TestSchema(BaseModel):
            sentiment: str
            confidence: float
        
        result = extract_json('{"sentiment": "BULLISH", "confidence": 85}', TestSchema)
        t.check(
            "Schema validation passes for valid data",
            result.get("sentiment") == "BULLISH",
            f"Got: {result}"
        )
        
        result = extract_json('{"wrong_field": "oops"}', TestSchema)
        t.check(
            "Schema validation failure returns validation errors or raw dict",
            "_validation_errors" in result or "wrong_field" in result or "error" in result,
            f"Got: {result}"
        )
    except ImportError:
        t.ok("Schema validation skipped (pydantic not available)")
    
    # --- Test 10: safe_parse_float ---
    t.check("safe_parse_float with float", safe_parse_float(3.14) == 3.14, "")
    t.check("safe_parse_float with string", safe_parse_float("42.5") == 42.5, "")
    t.check("safe_parse_float with None", safe_parse_float(None) == 0.0, "")
    t.check("safe_parse_float with invalid string", safe_parse_float("N/A", -1.0) == -1.0, "")
    t.check("safe_parse_float with int", safe_parse_float(10) == 10.0, "")
    
    return t.summary()

if __name__ == "__main__":
    success = test_json_extraction()
    sys.exit(0 if success else 1)
