import os
import ticket_analyzer_validator as tav
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


# -------------------------------
# 1️⃣ Environment / Email setup
# -------------------------------
TICKETS_CSV = os.path.join(os.getcwd(), 'tickets_sample.csv')
csv_path = os.environ.get('TICKETS_CSV', 'tickets_sample.csv')
tickets = tav.load_and_validate(csv_path)
weather = tav.fetch_weather(api_key='your_api_key', location='Hosur')
# 3️⃣ Generate report
REPORT_FILE = "ticket_analysis_report_executive.txt"
EMAIL_ON_EXEC = True  # Make sure this is True
EMAIL_TO = "harsha.nalamaru@gmail.com"
EMAIL_FROM = "nallamaru22@gmail.com"  # Replace with your Gmail
EMAIL_APP_PASSWORD = "iigz pzax cqzn xnaw"  # Replace with your Gmail App Password
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587  # TLS port

os.environ['TICKETS_CSV'] = TICKETS_CSV
os.environ['EMAIL_ON_EXEC'] = '1'
REPORT_FILE = os.path.join(os.getcwd(), "ticket_analysis_report_executive.txt")
# -------------------------------
# 2️⃣ Run ticket analyzer & generate reports
# -------------------------------
tickets, weather, metrics = tav.main()  # Make sure tav.main() returns these

# -------------------------------
# 3️⃣ Prepare the email
# -------------------------------
subject = "Support Ticket Analysis Report"
body = f"""\
Hi,

Please find attached the Support Ticket Executive Analysis Report.

This report includes:
- Overall ticket volume and open tickets
- Agent workload (idle vs overloaded)
- Priority and escalation insights
- Delay and trend analysis
- Weather context at ticket location

Regards,
Ticket Analysis System
"""

msg = MIMEMultipart()
msg['From'] = EMAIL_FROM
msg['To'] = EMAIL_TO
msg['Subject'] = subject
msg.attach(MIMEText(body, 'plain'))

# -------------------------------
# 4️⃣ Attach the report file
# -------------------------------
if os.path.exists(REPORT_FILE):
    with open(REPORT_FILE, "rb") as f:
        body = f.read().decode("utf-8", errors="ignore")
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename={os.path.basename(REPORT_FILE)}",
    )
    msg.attach(part)
else:
    print(f"Warning: Report file {REPORT_FILE} not found. Email will be sent without attachment.")

# 5  Send email via Gmail SMTP
# -------------------------------
try:
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
    server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    server.quit()
    print(f"Email successfully sent to {EMAIL_TO}")
except Exception as e:
    print(f"Failed to send email: {e}")
