# PokeBall

Logs unique source IPs from a Cowrie honeypot log into `pokeball_log.txt`.

## Usage

```bash
python3 catch-em-all.py --log /cowrie/var/log/cowrie/cowrie.json
```

## Continuous Run

Use `systemd` on the VPS to keep the script running continuously and restart it if it exits.
