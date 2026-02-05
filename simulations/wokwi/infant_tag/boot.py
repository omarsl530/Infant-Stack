print("Booting Infant Tag Simulation...")
import os
try:
    print("Filesystem content:", os.listdir())
except:
    print("Could not list filesystem.")

# Fallback to run main.py if not auto-started
try:
    import main
except ImportError:
    print("main.py not found!")
except Exception as e:
    print(f"Error running main.py: {e}")
