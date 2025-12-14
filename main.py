import os
import argparse
import json
import logging
from datetime import datetime, UTC
import send_ticket_email as ste
try:
    import ticket_analyzer_validator as tav
except Exception:
    tav = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def cli():
    parser = argparse.ArgumentParser(description="Ticket Analyzer CLI")
    parser.add_argument("--csv", help="Path to tickets CSV", default="tickets.csv")
    parser.add_argument("--use-validator", action="store_true", help="Run the consolidated validator/analyzer instead of built-in analyzer")
    parser.add_argument("--weather-key", help="Weather API key (optional)")
    parser.add_argument("--location", help="Weather location (optional)", default=None)
    parser.add_argument("--mock-weather", action="store_true", help="Use mock weather data (no real API call)")
    parser.add_argument("--force-refresh-weather", action="store_true", help="Delete existing weather cache and reports before running")
     # ✅ ADD THIS LINE
    parser.add_argument("--config", help="Path to JSON config file", default=None)
    args = parser.parse_args()
    # Load config file if provided
    if args.config and os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        logging.info("Loaded config file: %s", args.config)
    else:
        cfg = {}
    if args.weather_key:
        os.environ["WEATHER_API_KEY"] = args.weather_key
    if args.location:
        os.environ["LOCATION"] = args.location

    
    # If user didn't provide a CSV and a sample is available, prefer the sample
    # This makes `python main.py` work out-of-the-box for the provided sample dataset.
    if args.csv == "tickets.csv" and os.path.exists(os.path.join(os.getcwd(), "tickets_sample.csv")):
        args.csv = os.path.join(os.getcwd(), "tickets_sample.csv")

    # If requested, optionally force-refresh (delete) the cache and report files
    cache_path = os.path.join(os.getcwd(), "weather_cache.json")
    report_json = os.path.join(os.getcwd(), "ticket_analysis_report_summary.json")
    report_txt = os.path.join(os.getcwd(), "ticket_analysis_report_executive.txt")
    if args.force_refresh_weather:
        for p in (cache_path, report_json, report_txt):
            try:
                if os.path.exists(p):
                    os.remove(p)
                    logging.info("Removed existing file: %s", p)
            except Exception:
                pass

    # If requested, write a small weather cache file and set a fake key so validator loads cached weather
    if args.mock_weather:
        mock_data = {
            "weather": [{"description": "clear sky"}],
            "main": {"temp": 21.5},
            "name": args.location,
        }
        cache = {"ts": datetime.now(UTC).isoformat(), "data": mock_data}
        with open(cache_path, "w", encoding="utf-8") as fh:
            json.dump(cache, fh)
        os.environ["WEATHER_API_KEY"] = "MOCK_KEY"
        logging.info("Wrote mock weather to %s", cache_path)

    # Always delegate to the consolidated validator/analyzer
    if tav is None:
        logging.error("Error: 'ticket_analyzer_validator' module not found. Make sure the file exists.")
        return

    # set csv path for validator
    os.environ["TICKETS_CSV"] = args.csv
    # Call validator main which handles validation, analysis, weather and report generation
    tav.main()


if __name__ == "__main__":
    cli()