import sys

# test_run.py imports fcntl/pty/termios at module top, none exist on Windows
collect_ignore = ["test_run.py"] if sys.platform == "win32" else []
