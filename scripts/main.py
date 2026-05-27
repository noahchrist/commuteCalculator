import argparse
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import googlemaps
import yaml
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "responses.db")
CONFIG_PATH = os.path.join(BASE_DIR, "data", "config.yaml")
LOG_PATH = os.path.join(BASE_DIR, "data", "commute_scout.log")


def setup_logging():
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commute_samples (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            origin_label        TEXT NOT NULL,
            origin_address      TEXT NOT NULL,
            destination_label   TEXT NOT NULL,
            destination_address TEXT NOT NULL,
            departure_time      DATETIME NOT NULL,
            duration_seconds    INTEGER,
            distance_meters     INTEGER,
            direction           TEXT NOT NULL,
            raw_response        JSON,
            created_at          DATETIME NOT NULL
        )
    """)
    conn.commit()


def sample_pair(gmaps, origin, destination, direction, conn):
    cst = ZoneInfo("America/Chicago")
    now_utc = datetime.now(timezone.utc)
    now_cst = now_utc.astimezone(cst)
    try:
        result = gmaps.distance_matrix(
            origins=[origin["address"]],
            destinations=[destination["address"]],
            mode="driving",
            departure_time=now_utc,
            traffic_model="best_guess",
        )
        element = result["rows"][0]["elements"][0]
        if element["status"] != "OK":
            raise ValueError(f"API element status: {element['status']}")

        duration_seconds = element["duration_in_traffic"]["value"]
        distance_meters = element["distance"]["value"]

        conn.execute(
            """
            INSERT INTO commute_samples
                (origin_label, origin_address, destination_label, destination_address,
                 departure_time, duration_seconds, distance_meters, direction,
                 raw_response, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                origin["label"], origin["address"],
                destination["label"], destination["address"],
                now_cst.isoformat(),
                duration_seconds,
                distance_meters,
                direction,
                json.dumps(result),
                datetime.now(cst).isoformat(),
            ),
        )
        conn.commit()
        logging.info(
            "sampled %s -> %s: %ds / %dm",
            origin["label"], destination["label"], duration_seconds, distance_meters,
        )
    except Exception as exc:
        logging.error("failed %s -> %s: %s", origin["label"], destination["label"], exc)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Sample commute times via Google Maps.")
    parser.add_argument(
        "--direction",
        choices=["inbound", "outbound"],
        required=True,
        help="inbound = home→work, outbound = work→home",
    )
    args = parser.parse_args()

    setup_logging()

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logging.error("GOOGLE_MAPS_API_KEY is not set")
        raise SystemExit(1)

    try:
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
    except Exception as exc:
        logging.error("failed to load config: %s", exc)
        raise SystemExit(1)

    gmaps = googlemaps.Client(key=api_key)

    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        for origin in config["origins"]:
            for destination in config["destinations"]:
                sample_pair(gmaps, origin, destination, args.direction, conn)


if __name__ == "__main__":
    main()
