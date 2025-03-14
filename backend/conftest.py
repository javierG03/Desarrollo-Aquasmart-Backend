import sys
import os


def pytest_configure(config):
    # Get the absolute path to the project's root directory (where manage.py is, which is 'backend' directory)
    project_root = os.path.dirname(os.path.abspath(__file__))
    # Get the parent directory of the project root (which is 'DESARROLLO-AQUAS...' directory)
    parent_dir = os.path.dirname(project_root)

    # Add the parent directory to sys.path if it's not already there
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
