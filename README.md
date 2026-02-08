# Kimi Monitor

A lightweight monitor for Kimi usage quota reset events.

It checks usage data and sends email notifications when quota is reset.

## Features

- Monitors both weekly quota and 5-hour quota
- Detects reset by usage drop and reset-time jump
- Sends email notifications (SMTP)
- Supports background run and status/stop scripts
- Supports manual usage update from `/usage` output

## Project Structure

- `monitor.py`: main monitor loop
- `update_usage.py`: update usage state from CLI values
- `config.py`: configuration loader
- `notifier.py`: email/console notifier
- `state_manager.py`: reset-detection state logic
- `start-bg.sh`: start in background
- `stop.sh`: stop monitor
- `status.sh`: show monitor status
- `config.json.example`: config template

## Requirements

- Python 3.10+
- `requests`

## Quick Start

1. Install dependency:

```bash
python3 -m pip install requests
```

2. Create local config from template:

```bash
cp config.json.example config.json
```

3. Edit `config.json` with your own values:

```json
{
  "MOONSHOT_API_KEY": "",
  "SMTP_SERVER": "smtp.gmail.com",
  "SMTP_PORT": 587,
  "SMTP_USER": "your_email@gmail.com",
  "SMTP_PASSWORD": "your_app_password",
  "NOTIFY_EMAIL": "your_notify_email@example.com",
  "CHECK_INTERVAL_MINUTES": 10,
  "STATE_FILE": "/home/ubuntu/kimi-monitor/state.json",
  "LOG_FILE": "/home/ubuntu/kimi-monitor/monitor.log"
}
```

4. Update usage state after checking `/usage` in Kimi CLI:

```bash
./update_usage.py 84 6 22 54 19 3 54
```

5. Start monitor:

```bash
./start-bg.sh
```

6. Check status/log:

```bash
./status.sh
tail -f monitor.log
```

7. Stop monitor:

```bash
./stop.sh
```

## Usage Commands

```bash
# Show current state
./update_usage.py --show

# One-time check
python3 monitor.py --once

# Simulation mode
python3 monitor.py --simulate
```

## Security Notes

- Never commit `config.json` (contains secrets)
- Never commit logs/state files
- Rotate keys/passwords immediately if leaked
- Prefer environment variables in CI/production

`config.json`, runtime logs, PID/state files are ignored by `.gitignore`.

## Troubleshooting

- If email is not sent, check SMTP credentials and provider requirements.
- If background process exits, check `monitor.log`.
- If status shows stale PID, run `./stop.sh` then `./start-bg.sh`.
