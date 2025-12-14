import csv
import logging
from datetime import datetime
from typing import Dict, List, Tuple

DATE_FORMAT = "%Y-%m-%d"

# Allowed field validation
REQUIRED_FIELDS = [
    "ticket_id", "customer_id", "subject", "description",
    "priority", "status", "created_date", "assigned_to"
]

ALLOWED_PRIORITIES = ["Low", "Medium", "High", "Critical"]
ALLOWED_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]

logger = logging.getLogger(__name__)


class Ticket:
    def __init__(self, raw: Dict[str, str]):
        self.raw = raw
        self.ticket_id = raw.get("ticket_id")
        self.customer_id = raw.get("customer_id")
        self.subject = raw.get("subject", "").strip()
        self.description = raw.get("description", "").strip()
        self.priority = raw.get("priority")
        self.status = raw.get("status")
        self.created_date = self._parse_date(raw.get("created_date"))
        self.resolved_date = self._parse_date(raw.get("resolved_date"))
        self.assigned_to = raw.get("assigned_to")

    def _parse_date(self, val: str):
        if not val:
            return None
        try:
            return datetime.strptime(val.strip(), DATE_FORMAT).date()
        except Exception:
            raise ValueError(f"Invalid date: {val}")

    def resolution_days(self):
        if self.created_date and self.resolved_date:
            return (self.resolved_date - self.created_date).days
        return None


def load_tickets_from_csv(path: str) -> Tuple[List[Ticket], List[str]]:
    tickets = []
    errors = []

    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader, start=2):
                # Validate required fields
                missing = [
                    f for f in REQUIRED_FIELDS
                    if not (row.get(f) and row.get(f).strip())
                ]
                if missing:
                    msg = f"Row {i}: missing required fields: {missing}"
                    logger.warning(msg)
                    errors.append(msg)
                    continue

                # Validate priority
                if row.get("priority") not in ALLOWED_PRIORITIES:
                    msg = f"Row {i}: invalid priority: {row.get('priority')}"
                    logger.warning(msg)
                    errors.append(msg)
                    continue

                # Validate status
                if row.get("status") not in ALLOWED_STATUSES:
                    msg = f"Row {i}: invalid status: {row.get('status')}"
                    logger.warning(msg)
                    errors.append(msg)
                    continue

                # Parse ticket object
                try:
                    ticket = Ticket(row)
                    tickets.append(ticket)
                except Exception as e:
                    msg = f"Row {i}: error parsing ticket: {e}"
                    logger.warning(msg)
                    errors.append(msg)

    except FileNotFoundError:
        raise

    return tickets, errors


if __name__ == "__main__":
    # Minimal CLI so the module can be executed with `python -m ticket_analyzer`
    import argparse
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Run simple ticket analyzer module")
    parser.add_argument("--csv", help="Path to tickets CSV", default="tickets.csv")
    args = parser.parse_args()

    try:
        tickets, errors = load_tickets_from_csv(args.csv)
    except FileNotFoundError:
        logging.error("CSV file not found: %s", args.csv)
        raise

    logging.info("Loaded %d tickets, %d errors", len(tickets), len(errors))
    if errors:
        logging.info("Sample errors:")
        for e in errors[:5]:
            logging.info(" - %s", e)
    # print a small agents summary
    from collections import Counter

    agents = Counter(t.assigned_to for t in tickets if getattr(t, 'assigned_to', None))
    if agents:
        logging.info("Top agents:")
        for a, cnt in agents.most_common(5):
            logging.info(" - %s: %d", a, cnt)