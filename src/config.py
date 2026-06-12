import json
import argparse
from pathlib import Path

def load_client_config():
    # Load the parser
    parser = argparse.ArgumentParser()

    # Define our valid argument prefix'es
    parser.add_argument("--ip")
    parser.add_argument("--port", type=int)
    parser.add_argument("--mode")
    parser.add_argument("--password")

    # Bundle the args together
    args = parser.parse_args()

    # Extract values from inputted args
    IP = args.ip
    PORT = args.port
    MODE = args.mode
    PASSWORD = args.password

    return IP, PORT, MODE, PASSWORD

def load_server_config():
    # Same logic as above
    parser = argparse.ArgumentParser()
    parser.add_argument("--password")
    args = parser.parse_args()

    PASSWORD = args.password

    return PASSWORD