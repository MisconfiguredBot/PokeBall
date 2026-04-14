# PokeBall

PokeBall watches a Cowrie honeypot log, extracts client IP addresses, and writes each unique IP once to `pokeball_log.txt`.

It is designed to run continuously on the same VPS as Cowrie.

## What It Does

- Reads Cowrie JSON or text logs
- Extracts source IP addresses from past and new log entries
- Appends only new IPs to `pokeball_log.txt`
- Survives log rotation by reopening the active log file

## Files

- Script: `catch-em-all.py`
- Output: `pokeball_log.txt`

By default, the output file is written in the current working directory. In the `systemd` setup below, that means:

```bash
/home/cowrie/PokeBall/pokeball_log.txt
```

## Requirements

- Python 3
- A running Cowrie instance
- Permission for the service user to read the Cowrie log file

## Manual Run

Example using the active Cowrie JSON log:

```bash
python3 /home/cowrie/PokeBall/catch-em-all.py --log /home/cowrie/cowrie/var/log/cowrie/cowrie.json
```

If you made the script executable:

```bash
/home/cowrie/PokeBall/catch-em-all.py --log /home/cowrie/cowrie/var/log/cowrie/cowrie.json
```

## systemd Service

To keep the script running continuously, create this service file:

```ini
[Unit]
Description=Catch unique Cowrie IPs
After=network.target

[Service]
Type=simple
User=cowrie
WorkingDirectory=/home/cowrie/PokeBall
ExecStart=/usr/bin/python3 /home/cowrie/PokeBall/catch-em-all.py --log /home/cowrie/cowrie/var/log/cowrie/cowrie.json
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Save it as:

```bash
/etc/systemd/system/catch-em-all.service
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now catch-em-all.service
```

## Useful Commands

Check service status:

```bash
sudo systemctl status catch-em-all.service
```

Watch service logs:

```bash
sudo journalctl -u catch-em-all.service -f
```

Watch captured IPs:

```bash
tail -f /home/cowrie/PokeBall/pokeball_log.txt
```

Restart the service:

```bash
sudo systemctl restart catch-em-all.service
```

## Notes

- The script loads existing IPs from `pokeball_log.txt` on startup, so it does not duplicate entries after a restart.
- The default internal poll interval is 1 second.
- If the process exits, `systemd` restarts it after 5 seconds with the service file shown above.
