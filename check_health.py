#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Health check script for LLM Council backend."""

import sys
import os

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("LLM Council Health Check\n")
print("=" * 50)

# 1. Check Python version
print("\n1. Python Version:")
print(f"   [OK] Python {sys.version.split()[0]}")

# 2. Check critical imports
print("\n2. Checking Critical Imports:")
try:
    from backend import main
    print("   [OK] backend.main")
except Exception as e:
    print(f"   [ERROR] backend.main: {e}")
    sys.exit(1)

try:
    from backend import config
    print("   [OK] backend.config")
except Exception as e:
    print(f"   [ERROR] backend.config: {e}")
    sys.exit(1)

try:
    from backend import settings
    print("   [OK] backend.settings")
except Exception as e:
    print(f"   [ERROR] backend.settings: {e}")

try:
    from backend import memory
    print("   [OK] backend.memory")
except Exception as e:
    print(f"   [ERROR] backend.memory: {e}")

try:
    from backend import file_parser
    print("   [OK] backend.file_parser")
except Exception as e:
    print(f"   [ERROR] backend.file_parser: {e}")

# 3. Check API Key
print("\n3. Checking Configuration:")
if config.OPENROUTER_API_KEY:
    masked_key = config.OPENROUTER_API_KEY[:10] + "..." + config.OPENROUTER_API_KEY[-4:]
    print(f"   [OK] OPENROUTER_API_KEY: {masked_key}")
else:
    print("   [WARNING] OPENROUTER_API_KEY: NOT SET (check .env file)")

# 4. Check data directories
print("\n4. Checking Data Directories:")
data_dirs = ["data", "data/conversations"]
for dir_path in data_dirs:
    if os.path.exists(dir_path):
        print(f"   [OK] {dir_path}")
    else:
        print(f"   [INFO] {dir_path} (will be created on first use)")

# Check settings file
settings_file = "data/settings.json"
if os.path.exists(settings_file):
    print(f"   [OK] {settings_file}")
else:
    print(f"   [INFO] {settings_file} (will be created on first use)")

# 5. Check dependencies
print("\n5. Checking Dependencies:")
deps = {
    "fastapi": "FastAPI",
    "uvicorn": "Uvicorn",
    "httpx": "HTTPX",
    "pandas": "Pandas",
    "pypdf": "PyPDF",
    "tabulate": "Tabulate",
    "yfinance": "Yahoo Finance",
    "fpdf": "FPDF",
}

for module, name in deps.items():
    try:
        __import__(module)
        print(f"   [OK] {name}")
    except ImportError:
        print(f"   [ERROR] {name} (missing)")

# 6. Check settings file
print("\n6. Checking Settings:")
try:
    settings_data = settings.load_settings()
    watchlist = settings.get_watchlist()
    print(f"   [OK] Settings loaded: {len(watchlist)} tickers in watchlist")
except Exception as e:
    print(f"   [ERROR] Settings error: {e}")

# 7. Check memory file
print("\n7. Checking Memory System:")
try:
    from backend import memory
    context = memory.get_relevant_context(limit=1)
    if context:
        print(f"   [OK] Memory system working ({len(context)} chars retrieved)")
    else:
        print("   [INFO] Memory system empty (normal for first run)")
except Exception as e:
    print(f"   [ERROR] Memory error: {e}")

# 8. Test file parser
print("\n8. Testing File Parser:")
try:
    import pandas as pd
    df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    markdown = df.to_markdown(index=False)
    print("   [OK] Pandas to_markdown() working")
except Exception as e:
    print(f"   [ERROR] File parser test failed: {e}")

print("\n" + "=" * 50)
print("[OK] Health check complete!")
print("\nIf you see any [ERROR] messages above, those need to be fixed.")
print("If all checks pass, the backend should work correctly.")
