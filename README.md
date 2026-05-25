# Commute Calculator

Periodically samples traffic-aware drive times between a set of origin/destination pairs using the Google Maps Distance Matrix API and stores the results in a local SQLite database. Designed to accumulate data over weeks for offline analysis.

Currently configured to scout morning and evening commute times between several Chicago neighborhoods and an office in Oak Brook, IL — but the inputs are fully config-driven and can be pointed at any addresses.

## How it works

A cron job invokes the script once per sample. The script reads `data/config.yaml`, calls the Distance Matrix API for every origin → destination pair using the current time as `departure_time`, and writes each result to `data/responses.db`. No persistent process required.

## Setup

```bash
pip3 install -r requirements.txt
```

Add your GOOGLE_MAPS_API_KEY to .env
Update `data/config.yaml` with your origins and destinations.

## Usage

```bash
python3 scripts/main.py --direction inbound   # home → work
python3 scripts/main.py --direction outbound  # work → home
```

## Crontab example

```
# Sample inbound commute times on weekday mornings
0 7,8,9 * * 1-5 cd ~/projects/commuteCalculator && python3 scripts/main.py --direction inbound

# Sample outbound commute times on weekday afternoons
0 16,17,18 * * 1-5 cd ~/projects/commuteCalculator && python3 scripts/main.py --direction outbound
```

## Config

Edit `data/config.yaml` to add or remove origins and destinations — no code changes needed.

## Output

Results are written to `data/responses.db` (SQLite). Each row includes origin/destination labels and addresses, departure time, traffic-aware duration, distance, direction, and the full raw API response.

Errors are logged to `data/commute_scout.log`.
