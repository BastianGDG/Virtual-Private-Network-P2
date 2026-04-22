## VPN Project

Super simple guide to run the project.

## Requirements

- Python 3.12+
- uv installed
- Linux (TUN + networking commands)

## Setup

```bash
uv sync
```

## Run server

```bash
sudo -E uv run python src/server.py --password <PASSWORD>
```

Example:

```bash
sudo -E uv run python src/server.py --password hello
```

## Run client

```bash
sudo -E uv run python src/client.py --ip <SERVER_IP> --port 6789 --mode local --password <PASSWORD>
```

Example:

```bash
sudo -E uv run python src/client.py --ip 192.168.1.170 --port 6789 --mode local --password hello
```

## Notes

- Start the server first.
- Server and client must use the same password.
