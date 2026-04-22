import json
import argparse
from pathlib import Path

def load_client_config():
    ROOT = Path(__file__).resolve().parent.parent
    
    config_path = ROOT / "config" / "config.json"

    with open(config_path) as f:
        config = json.load(f)

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip")
    parser.add_argument("--port", type=int)
    parser.add_argument("--mode")
    parser.add_argument("--password")
    args = parser.parse_args()

    IP = args.ip or config["server_ip"]
    PORT = args.port or config["port"]
    MODE = args.mode or config["mode"]
    PASSWORD = args.password or config["password"]

    return IP, PORT, MODE, PASSWORD

def load_server_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("--password")
    args = parser.parse_args()

    PASSWORD = args.password

    return PASSWORD