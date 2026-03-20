import runpy
import os
import sys

# Run src/web_app.py from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
runpy.run_path(os.path.join(os.path.dirname(__file__), "src", "web_app.py"), run_name="__main__")
