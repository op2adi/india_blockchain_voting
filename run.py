#!/usr/bin/env python
"""
Startup script for the India Blockchain Voting System
This script will:
1. Check for missing migrations
2. Apply migrations
3. Create a superuser if one doesn't exist
4. Start the Django development server
"""
import os
import sys
import subprocess
import time

def run_command(command, check=True):
    """Run a shell command and return output"""
    print(f"Running command: {command}")
    return subprocess.run(command, shell=True, check=check, text=True)

def main():
    print("Starting India Blockchain Voting System...")
    
    # Set environment variables if needed
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'india_blockchain_voting.settings')
    
    # Check for migrations
    print("\n=== Checking for migrations ===")
    run_command("python manage.py makemigrations")
    
    # Apply migrations
    print("\n=== Applying migrations ===")
    run_command("python manage.py migrate")
    
    # Create superuser if needed
    print("\n=== Checking for superuser ===")
    try:
        run_command("python manage.py create_admin_user", check=False)
    except subprocess.CalledProcessError:
        print("Error creating superuser - may already exist")
    
    # Start the development server
    print("\n=== Starting development server ===")
    run_command("python manage.py runserver 0.0.0.0:8000")

if __name__ == "__main__":
    main()
