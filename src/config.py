import json
import argparse
from pathlib import Path

def load_config():
    ROOT = Path(__file__).resolve().parent.parent
    
    config_path = ROOT / "config" / "config.json"

    with open(config_path) as f:
        config = json.load(f)

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip")
    parser.add_argument("--port", type=int)
    parser.add_argument("--mode")
    args = parser.parse_args()

    IP = args.ip or config["server_ip"]
    PORT = args.port or config["port"]
    MODE = args.mode or config["mode"]

    return IP, PORT, MODE