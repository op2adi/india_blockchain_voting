import os
import sys
import subprocess

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Run the Django management command
try:
    command = [sys.executable, 'manage.py', 'migrate']
    result = subprocess.run(command, cwd=script_dir, check=True, capture_output=True, text=True)
    print("Command output:")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print("Error running command:")
    print(e.stderr)
except Exception as e:
    print("Exception:", str(e))
