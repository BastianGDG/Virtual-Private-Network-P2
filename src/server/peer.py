import json
import datetime
import os

PEER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "peer.json"))

os.makedirs(os.path.dirname(PEER_PATH), exist_ok=True)

if not os.path.exists(PEER_PATH):
    with open(PEER_PATH, "w") as file:
        json.dump([], file)

def create_peer(ID, IP, key):
    # Create class with placeholder attributes for a peer
    class createPeer:
        def __init__(self, ID, IP, key):
            self.ID = ID
            self.IP = IP
            self.Virtual_IP = "10.0.0." + ID
            self.key = key
            self.last_seen = str(datetime.datetime.now())

    # Create a new object peer, with the given parameters for the function
    peer = createPeer(ID, IP, key)

    # Send peer to be updated in peer.json
    update_table(peer)

    # Return the object
    return peer

def update_table(peer):
    # Create placeholder array for data, this is used to temporarly carry written data from peer.json, so it does not get overwritten
    data = []

    # Use __dict__ to extract data from object  
    peer = peer.__dict__

    # Try opening the file in read mode, then extract the contents into data[], expect if it does not exist, simply pass
    try:
        with open(PEER_PATH, "r") as file:
            data.extend(json.load(file))
    except:
        pass
    
    # Check if the current ID of the item to be indexed, already exists
    for item in range(len(data)):
        if peer["ID"] == data[item]["ID"]:
            data.pop(item)

    # Append data[] with the new peer  
    data.append(peer)

    # Write data, alongside the older peers, into peer.json, use indent 4 for cleaner formatting
    with open(PEER_PATH, "w") as file:
        json.dump(data, file, indent=4)

def flush_table():
    # Delete everything and replace with [ ]
    with open(PEER_PATH, "w") as f:
        json.dump([], f)

def lookup(ID):
    with open(PEER_PATH, "r") as f:
        data = json.load(f)
    # Search for the given ID, set None flag so the program does nothing if it can't be found
    try:
        search = next((item for item in data if item["ID"] == ID), None)

        # The peer needs to be recreated from the lookup, to ensure the object exists between runs
        result = create_peer(search["ID"],search["IP"],search["key"])
        return result
    # If the search fails the ID likely does not exist
    except:
        return None

def edit_peer(ID, option, input):
    with open(PEER_PATH, "r") as f:
        data = json.load(f)
    # Same logic as lookup, expect when we're recreating the object, we're injecting the new input on the given option into the new object
    try:
        search = next((item for item in data if item["ID"] == ID), None)
        search[option] = input

        create_peer(search["ID"],search["IP"],search["key"],search["counter"])
    except:
        print("ID not found or invalid option")
