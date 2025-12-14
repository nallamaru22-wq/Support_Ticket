from __future__ import annotations
import csv
import json
import logging
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta, UTC
from typing import Dict, Iterable, List, Optional, Tuple
import smtplib
from email.message import EmailMessage

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ---------------- CONSTANTS ---------------- #

REQUIRED_FIELDS = [
    "ticket_id",
    "customer_id",
    "subject",
    "description",
    "priority",
    "status",
    "created_date",
    "resolved_date",
    "assigned_to",
]

PRIORITIES = {"Low", "Medium", "High", "Critical"}
STATUSES = {"Open", "In Progress", "Resolved", "Closed"}
DATE_FMT = "%Y-%m-%d"

STOP_WORDS = {
    "the", "and", "is", "in", "to", "a", "of", "for", "on", "with"
}

# Default thresholds (configurable via ENV or CLI)
IDLE_THRESHOLD = int(os.environ.get("IDLE_THRESHOLD", 2))
OVERLOAD_THRESHOLD = int(os.environ.get("OVERLOAD_THRESHOLD", 6))
BACKLOG_DAYS = int(os.environ.get("BACKLOG_DAYS", 7))

#-------------------email settings-------------------#
def send_execution_email(report_path: str):
    """
    Send ticket analysis report via email.
    Requires environment variables:
        ALERT_SMTP_HOST
        ALERT_SMTP_PORT
        ALERT_EMAIL_FROM
        EXEC_EMAIL_TO
    """
    smtp_host = os.environ.get("ALERT_SMTP_HOST", "localhost")
    smtp_port = int(os.environ.get("ALERT_SMTP_PORT", 25))
    email_from = os.environ.get("ALERT_EMAIL_FROM")
    email_to = os.environ.get("EXEC_EMAIL_TO")

    

    # Read the report file
    with open(report_path, "r", encoding="utf-8") as f:
        body = f.read()

    msg = EmailMessage()
    msg['From'] = email_from
    msg['To'] = email_to
    msg['Subject'] = "Support Ticket Analysis Report"
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.send_message(msg)
        print(f"Email sent successfully to {email_to}")
    except Exception as e:
        print(f"Failed to send email: {e}")
# ---------------- CSV + VALIDATION ---------------- #

def parse_date(s: str) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), DATE_FMT).date()
    except Exception:
        return None


def load_and_validate(csv_path: str) -> Tuple[List[Dict], List[Dict]]:
    valid = []
    errors = []

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        for row_num, row in enumerate(reader, start=2):
            row_errors = []

            # Strip string fields
            for k, v in row.items():
                row[k] = v.strip() if isinstance(v, str) else v

            # Required fields (resolved_date is optional)
            for field in REQUIRED_FIELDS:
                if field == "resolved_date":
                    continue
                if field not in row or not row[field]:
                    row_errors.append(f"missing field: {field}")

            # Validate priority
            if row.get("priority") not in PRIORITIES:
                row_errors.append(f"invalid priority: {row.get('priority')}")

            # Validate status
            if row.get("status") not in STATUSES:
                row_errors.append(f"invalid status: {row.get('status')}")

            # Parse dates
            created = parse_date(row.get("created_date", ""))
            resolved = parse_date(row.get("resolved_date", ""))

            if row.get("created_date") and not created:
                row_errors.append(f"invalid created_date: {row.get('created_date')}")

            if row.get("resolved_date") and not resolved:
                row_errors.append(f"invalid resolved_date: {row.get('resolved_date')}")

            if row_errors:
                errors.append({
                    "row": row_num,
                    "ticket_id": row.get("ticket_id"),
                    "errors": row_errors
                })
            else:
                row["created_date"] = created
                row["resolved_date"] = resolved
                valid.append(row)

    return valid, errors




# ---------------- BASIC METRICS ---------------- #

def resolution_days(t: Dict) -> Optional[int]:
    if t.get("created_date") and t.get("resolved_date"):
        return (t["resolved_date"] - t["created_date"]).days
    return None


def avg_resolution_by_priority(tickets: Iterable[Dict]) -> Dict[str, float]:
    sums = defaultdict(list)
    for t in tickets:
        d = resolution_days(t)
        if d is not None:
            sums[t["priority"]].append(d)
    return {p: (sum(v) / len(v)) for p, v in sums.items()}


def tickets_open_more_than(tickets: Iterable[Dict], days: int = 7) -> List[Dict]:
    today = date.today()
    return [
        t for t in tickets
        if t["status"] not in {"Resolved", "Closed"}
        and t.get("created_date")
        and (today - t["created_date"]).days > days
    ]


def count_by_status_and_priority(tickets: Iterable[Dict]) -> Dict[str, Dict[str, int]]:
    counts = {s: {p: 0 for p in PRIORITIES} for s in STATUSES}
    for t in tickets:
        counts[t["status"]][t["priority"]] += 1
    return counts


def resolved_by_agent(tickets: Iterable[Dict]) -> Counter:
    c = Counter()
    for t in tickets:
        if t["status"] in {"Resolved", "Closed"}:
            c[t["assigned_to"]] += 1
    return c


def avg_resolution_per_agent(tickets: Iterable[Dict]) -> Dict[str, float]:
    sums = defaultdict(list)
    for t in tickets:
        d = resolution_days(t)
        if d is not None:
            sums[t["assigned_to"]].append(d)
    return {a: sum(v) / len(v) for a, v in sums.items()}


# ---------------- NEW FEATURES ---------------- #

def agent_workload(tickets: List[Dict]) -> Dict:
    active = defaultdict(int)
    for t in tickets:
        if t["status"] in {"Open", "In Progress"}:
            active[t["assigned_to"]] += 1

    return {
        "active_per_agent": dict(active),
        "idle_agents": [a for a, c in active.items() if c <= IDLE_THRESHOLD],
        "overloaded_agents": [a for a, c in active.items() if c >= OVERLOAD_THRESHOLD],
    }


def repeat_issues(tickets: List[Dict], ngram: int = 2) -> Dict:
    subjects = [t["subject"].lower() for t in tickets if t.get("subject")]
    subject_counts = Counter(subjects)

    words = []
    for s in subjects:
        words.extend(w for w in re.findall(r"\w+", s) if w not in STOP_WORDS)

    ngrams = zip(*[words[i:] for i in range(ngram)])
    return {
        "repeated_subjects": {s: c for s, c in subject_counts.items() if c > 1},
        "common_ngrams": Counter(ngrams).most_common(10)
    }


def delay_reasons(tickets: List[Dict]) -> Dict[str, List[str]]:
    today = date.today()
    delays = {}

    for t in tickets:
        reasons = []
        if not t.get("assigned_to"):
            reasons.append("Missing assignee")
        if len(t.get("description", "")) < 10:
            reasons.append("Short description")
        if t.get("created_date") and t["created_date"].weekday() >= 5:
            reasons.append("Weekend created")
        if (
            t["status"] not in {"Resolved", "Closed"}
            and t.get("created_date")
            and (today - t["created_date"]).days > BACKLOG_DAYS
        ):
            reasons.append("Backlog")

        if reasons:
            delays[t["ticket_id"]] = reasons

    return delays


def volume_by_weekday(tickets: List[Dict]) -> Dict[str, int]:
    c = Counter()
    for t in tickets:
        if t.get("created_date"):
            c[t["created_date"].strftime("%A")] += 1
    return dict(c)


def priority_escalation(tickets: List[Dict]) -> List[Tuple[str, str, str]]:
    order = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    escalations = []
    prev = {}

    tickets = sorted(tickets, key=lambda x: (x["customer_id"], x["created_date"] or date.min))
    for t in tickets:
        curr = order.get(t["priority"], 0)
        last = prev.get(t["customer_id"], 0)
        if curr > last:
            escalations.append((t["customer_id"], t["ticket_id"], t["priority"]))
        prev[t["customer_id"]] = curr

    return escalations


# ---------------- WEATHER (UNCHANGED, SAFE) ---------------- #

def fetch_weather(api_key: str, location: Optional[str], cache_file="weather_cache.json", ttl=600):
    if not api_key:
        return None

    location = location or "hosur"

    try:
        if os.path.exists(cache_file):
            cache = json.load(open(cache_file))
            ts = datetime.fromisoformat(cache["ts"])
            if datetime.now(UTC) - ts < timedelta(seconds=ttl):
                if cache["data"].get("name", "").lower() == location.lower():
                    return cache["data"]
    except Exception:
        pass

    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": location, "appid": api_key, "units": "metric"},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        if "weather" not in data:
            return None
        json.dump({"ts": datetime.now(UTC).isoformat(), "data": data}, open(cache_file, "w"))
        return data
    except Exception:
        return None


# ---------------- REPORTS ---------------- #

def generate_reports(tickets: List[Dict], weather: Optional[dict], out_prefix="ticket_analysis_report"):
    total = len(tickets)
    open_count = sum(1 for t in tickets if t["status"] not in {"Resolved", "Closed"})
    avg_res_by_prio = avg_resolution_by_priority(tickets)
    perf = resolved_by_agent(tickets)
    top_agents = perf.most_common(3)
    metrics = {
        "total_tickets": len(tickets),
        "open_tickets": sum(t["status"] not in {"Resolved", "Closed"} for t in tickets),
        "avg_resolution_by_priority": avg_resolution_by_priority(tickets),
        "tickets_open_gt_7_days": len(tickets_open_more_than(tickets)),
        "counts_by_status_and_priority": count_by_status_and_priority(tickets),
        "resolved_per_agent": dict(perf),
        "top_agents": perf.most_common(3),
        "avg_resolution_per_agent": avg_resolution_per_agent(tickets),
        "monthly_trends": dict(Counter(
            f"{t['created_date'].year}-{t['created_date'].month:02d}"
            for t in tickets if t.get("created_date")
        )),
        "common_subject_words": Counter(
            w for t in tickets for w in re.findall(r"\w+", t["subject"].lower())
            if w not in STOP_WORDS
        ).most_common(30),
        "customers_with_many_tickets": Counter(
            t["customer_id"] for t in tickets
        ).most_common(),
        "agent_workload": agent_workload(tickets),
        "repeat_issues": repeat_issues(tickets),
        "delay_reasons": delay_reasons(tickets),
        "volume_by_weekday": volume_by_weekday(tickets),
        "priority_escalation": priority_escalation(tickets),
        "weather": weather,
    }

    json.dump(metrics, open(f"{out_prefix}_summary.json", "w"), indent=2, default=str)
    exec_report= f"{out_prefix}_executive.txt"
    with open(exec_report, "w") as f:
        f.write("Support Ticket Executive Summary\n")
        f.write(f"Generated: {datetime.utcnow().date()}\n\n")
        f.write("=== Summary Statistics ===\n")
        f.write(f"Total Tickets: {metrics['total_tickets']}\n")
        f.write(f"Open Tickets: {metrics['open_tickets']}\n")
        f.write(f"Tickets Open > 7 Days: {metrics['tickets_open_gt_7_days']}\n\n")
        f.write("=== Agent Workload ===\n")
        f.write(f"Idle Agents: {metrics['agent_workload']['idle_agents']}\n")
        f.write(f"Overloaded Agents: {metrics['agent_workload']['overloaded_agents']}\n")
        f.write("=== Performance Highlights ===\n")
        if top_agents:
            agent, cnt = top_agents[0]
            f.write(f"Top Performer: {agent} ({cnt} tickets resolved)\n")

        avg_all = (
            sum(avg_res_by_prio.values()) / len(avg_res_by_prio)
            if avg_res_by_prio else 0
        )
        f.write(f"Average Resolution Time: {avg_all:.2f} days\n\n")

        f.write("=== Observations & Recommendations ===\n")
        f.write("- Reassign tickets from overloaded agents to idle agents.\n")
        f.write("- Review long-open tickets to prevent SLA breaches.\n")
        f.write("- Monitor repeat customer issues for proactive escalation.\n")

        if weather:
            try:
                desc = weather["weather"][0]["description"]
                temp = weather["main"]["temp"]
                city = weather.get("name")
                f.write(f"\nWeather at {city}: {desc}, {temp}°C\n")
            except Exception:
                pass
    return metrics, exec_report

#new
def most_common_subject_words(tickets: List[Dict], topn: int = 10) -> List[tuple]:
    words = []
    for t in tickets:
        subject = t.get("subject", "")
        for w in re.findall(r"\w+", subject.lower()):
            if w not in STOP_WORDS:
                words.append(w)
    return Counter(words).most_common(topn)



# ---------------- MAIN ---------------- #

def main():
    csv_path = os.environ.get("TICKETS_CSV", "tickets.csv")
    api_key = os.environ.get("WEATHER_API_KEY")
    location = os.environ.get("LOCATION", "hosur")
    tickets, errors = load_and_validate(csv_path)
    weather = fetch_weather(api_key, location) if api_key else None
    
    # Generate reports
    metrics = generate_reports(tickets, weather, out_prefix="ticket_analysis_report")

    # Send executive report email if enabled
    #if os.environ.get("EMAIL_ON_EXEC") == "1":
        #send_execution_email("ticket_analysis_report_executive.txt")
    #logging.info("Done.")
    return tickets, weather,metrics
    

if __name__ == "__main__":
    main()
