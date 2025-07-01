#!/usr/bin/env python
"""
Multi-node blockchain network script for India Blockchain Voting System
This script will start multiple instances of the application as separate blockchain nodes
"""
import os
import subprocess
import time
import threading
import socket
import sys

# Define node settings
nodes = [
    {"id": "node1", "port": 8001, "peers": ["http://localhost:8002", "http://localhost:8003"]},
    {"id": "node2", "port": 8002, "peers": ["http://localhost:8001", "http://localhost:8003"]},
    {"id": "node3", "port": 8003, "peers": ["http://localhost:8001", "http://localhost:8002"]},
]

def is_port_available(port):
    """Check if a port is available to use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def start_node(node_config):
    """Start a blockchain node with the given configuration"""
    node_id = node_config["id"]
    port = node_config["port"]
    peers = ",".join(node_config["peers"])
    
    print(f"Starting blockchain node {node_id} on port {port}...")
    
    if not is_port_available(port):
        print(f"Error: Port {port} is already in use. Node {node_id} will not start.")
        return
    
    # Set environment variables for this node
    env = os.environ.copy()
    env["BLOCKCHAIN_NODE_ID"] = node_id
    env["BLOCKCHAIN_NODE_URL"] = f"http://localhost:{port}"
    env["BLOCKCHAIN_KNOWN_NODES"] = peers
    
    # Use a custom settings file or command-line args to specify node settings
    cmd = f"python manage.py runserver 0.0.0.0:{port}"
    
    # Start the node in a new process
    process = subprocess.Popen(cmd, shell=True, env=env)
    return process

def main():
    """Main function to start all blockchain nodes"""
    processes = []
    
    try:
        # First apply migrations using the default node
        print("Setting up database...")
        subprocess.run("python manage.py migrate", shell=True, check=True)
        
        # Start all blockchain nodes
        for node_config in nodes:
            process = start_node(node_config)
            if process:
                processes.append(process)
                # Small delay to avoid port conflicts during startup
                time.sleep(1)
        
        print(f"\n{len(processes)} blockchain nodes running. Press Ctrl+C to stop all nodes.")
        
        # Wait for all processes to complete (will only happen on keyboard interrupt)
        for process in processes:
            process.wait()
            
    except KeyboardInterrupt:
        print("\nShutting down all blockchain nodes...")
        for process in processes:
            process.terminate()
        
        # Wait for processes to terminate
        for process in processes:
            process.wait()
            
        print("All nodes stopped.")

if __name__ == "__main__":
    main()
