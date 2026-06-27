"""Pytest configuration for tests."""

import sys
from pathlib import Path

# When running pytest from WindowsAIAssistant root, ensure backend is importable
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Also ensure the parent directory (WindowsAIAssistant) is in path for 'backend' imports
windows_ai_dir = backend_dir.parent
if str(windows_ai_dir) not in sys.path:
    sys.path.insert(0, str(windows_ai_dir))


