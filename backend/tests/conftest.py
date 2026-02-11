"""
Shared test utilities for all test files.
"""
import sys
import os
import asyncio
from pathlib import Path

# Ensure backend is importable
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Provide an event loop for async tests
def run_async(coro):
    """Helper to run async functions in sync test scripts."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def ok(self, name: str):
        self.passed += 1
        print(f"  ✅ {name}")
    
    def fail(self, name: str, reason: str = ""):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ❌ {name}: {reason}")
    
    def check(self, name: str, condition: bool, fail_reason: str = ""):
        if condition:
            self.ok(name)
        else:
            self.fail(name, fail_reason)
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"Results: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailures:")
            for name, reason in self.errors:
                print(f"  ❌ {name}: {reason}")
        print(f"{'='*50}")
        return self.failed == 0
