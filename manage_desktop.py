#!/usr/bin/env python
"""manage.py for the desktop settings (uses the AppData database)."""

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "desktop.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
