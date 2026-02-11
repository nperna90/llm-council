"""Utility functions for parsing and validation."""

import json
import re
from typing import Any, Optional, Union

try:
    from pydantic import BaseModel, ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = None
    ValidationError = None
    PYDANTIC_AVAILABLE = False


def extract_json(text: str, schema_class: Optional[type] = None) -> dict:
    """
    Extract and parse JSON from text using multiple fallback strategies.
    
    Tries in order:
    1. Direct JSON parse
    2. Extract from markdown code fences (```json ... ```)
    3. Find first {...} or [...] block via regex
    4. Return error dict if all strategies fail
    
    Args:
        text: Raw text that may contain JSON
        schema_class: Optional Pydantic BaseModel class for validation
        
    Returns:
        Parsed JSON dict. If parsing fails, returns {"error": "...", "raw_text": "..."}.
        If schema validation fails, adds "_validation_errors" key to the dict.
    """
    if not text or not isinstance(text, str):
        return {"error": "Empty or invalid input", "raw_text": str(text)[:500]}
    
    parsed_data = None
    
    # Strategy 1: Direct JSON parse
    try:
        parsed_data = json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from markdown code fences
    if parsed_data is None:
        markdown_pattern = r'```(?:json)?\s*\n(.*?)\n```'
        matches = re.findall(markdown_pattern, text, re.DOTALL)
        if matches:
            try:
                parsed_data = json.loads(matches[0])
            except json.JSONDecodeError:
                pass
    
    # Strategy 3: Find first {...} or [...] block
    if parsed_data is None:
        # Try to find object
        obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        obj_match = re.search(obj_pattern, text, re.DOTALL)
        if obj_match:
            try:
                parsed_data = json.loads(obj_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # If object didn't work, try array
        if parsed_data is None:
            arr_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
            arr_match = re.search(arr_pattern, text, re.DOTALL)
            if arr_match:
                try:
                    parsed_data = json.loads(arr_match.group(0))
                except json.JSONDecodeError:
                    pass
    
    # Strategy 4: Return error dict
    if parsed_data is None:
        return {
            "error": "Failed to extract valid JSON from text",
            "raw_text": text[:500]
        }
    
    # Validate against schema if provided
    if schema_class is not None and PYDANTIC_AVAILABLE and parsed_data:
        try:
            # Validate using Pydantic
            if isinstance(schema_class, type) and issubclass(schema_class, BaseModel):
                schema_class.model_validate(parsed_data)
        except ValidationError as e:
            # Add validation errors to the dict
            if isinstance(parsed_data, dict):
                parsed_data["_validation_errors"] = [
                    {"field": err["loc"], "message": err["msg"]} 
                    for err in e.errors()
                ]
        except Exception as e:
            # Handle other validation errors
            if isinstance(parsed_data, dict):
                parsed_data["_validation_errors"] = [{"error": str(e)}]
    
    return parsed_data


def safe_parse_float(value: Any, default: float = 0.0) -> float:
    """
    Safely parse a value to float with fallback.
    
    Handles strings, None, and other types that might appear in LLM outputs
    or user input.
    
    Args:
        value: Value to parse (can be str, int, float, None, etc.)
        default: Default value if parsing fails
        
    Returns:
        Parsed float value or default
    """
    if value is None:
        return default
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Remove common formatting characters
        cleaned = value.strip().replace(',', '').replace('$', '').replace('%', '')
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return default
    
    # For any other type, try direct conversion
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
