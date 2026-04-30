# VPN Project

## Requirements

- Python 3.12+
- uv
- Linux with TUN support

## Install

```bash
uv sync
```

## Run

Start the server from the project root:

```bash
sudo -E uv run python -m src.server.server --password <PASSWORD>
```

Start the client from the project root:

```bash
sudo -E uv run python -m src.client.client --ip <SERVER_IP> --port 6789 --mode <local|global> --password <PASSWORD>
```

## Notes

- Start the server first.
- Use the same password on both sides.
- Use `local` for a local network and `global` for a remote network.
