# Final Assessment Submission – Ticket Analyzer Validator

## 1️⃣ Summary

This submission provides a concise support ticket analysis tool that validates, analyzes, and reports on support tickets while integrating optional weather data.

**Core Features:**

- Validates ticket CSV files (`ticket_analyzer_validator.py`).
- Computes analysis metrics:
  - Average resolution time per priority.
  - Open ticket counts.
  - Status and priority breakdown.
  - Agent performance.
  - Monthly trends.
  - Most common subject words.
  - High-volume customers.
- Integrates weather data (OpenWeatherMap) with file-based caching and TTL.
- Generates two report files:
  - `ticket_analysis_report_summary.json` — machine-readable metrics.
  - `ticket_analysis_report_executive.txt` — human-readable executive summary.
- Includes a CLI wrapper (`main.py`) and unit tests (`tests/`).

---

## 2️⃣ New Implementations

**Agent Workload & Utilization**

- Identifies idle agents (underloaded) and overloaded agents.
- Supports proactive ticket reassignment to balance workloads.

**Repeat Issue & Escalation Detection**

- Detects repeated ticket subjects and frequent n-grams.
- Highlights priority escalation sequences per customer.

**Delay Reason Analysis**

Flags tickets delayed due to:

- Missing assignee.
- Insufficient description.
- Creation on weekends.
- Backlogs.

**Ticket Volume Trends**

- Weekly and monthly ticket trends for staffing and escalation planning.

**Priority Escalation Insights**

- Highlights customers whose issues escalate in severity.

**CLI & Configuration Enhancements**

Supports:

- Weather API integration.
- Mock weather for offline testing.
- Location-specific weather lookups.
- Thresholds and alerts configurable via environment variables.

**Weather Integration**

- Fetches weather data from OpenWeatherMap API.
- File-based caching with TTL reduces repeated API calls.
- Mock mode available for offline testing.

**Report Generation**

- Executive Summary: `ticket_analysis_report_executive.txt`.
- JSON Metrics: `ticket_analysis_report_summary.json`.

**Notifications & Alerts**

- Sends execution emails via SMTP (Gmail App Password supported).
- Includes report file attachments.
- Extensible for Slack or other alert integrations.

**Testing Enhancements**

Unit tests added for:

- Weather caching.
- Invalid ticket data.
- Escalation detection.
- Delay reason analysis.

All tests passing with Python’s built-in `unittest`.

---

## 3️⃣ How to Run

### 3.1 Setup
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

### 3.2 Run Tests
python -m unittest discover -v tests

### 3.3 With Mock Weather
python main.py --mock-weather --location "Hosur"

## 4️⃣ Notes

- **Cache file:** `weather_cache.json`

- **Output files:**
  - `ticket_analysis_report_summary.json`
  - `ticket_analysis_report_executive.txt`

- **Email reports:** Uses Gmail SMTP with App Password.

- **Configuration:** Thresholds and settings can be modified via environment variables.


