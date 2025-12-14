import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import ticket_analyzer_validator as tav


SAMPLE_CSV = """ticket_id,customer_id,subject,description,priority,status,created_date,resolved_date,assigned_to
T1,C1,Login error,Can't login,High,Resolved,2024-10-01,2024-10-02,Agent_X
T2,C2,Slow,App slow,Medium,In Progress,2024-11-01,,Agent_Y
T3,C1,Request,Please add feature,Low,Open,2024-10-20,,Agent_X
T4,C3,Bug,Broken page,Critical,Resolved,2024-09-10,2024-09-12,Agent_Z
T5,C4,Bad date,Invalid date,Low,Resolved,2024-13-01,2024-13-02,Agent_X
"""


class TicketAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8")
        self.tmp.write(SAMPLE_CSV)
        self.tmp.flush()
        self.tmp.close()

    def tearDown(self):
        try:
            os.unlink(self.tmp.name)
        except Exception:
            pass

    def test_load_and_validate_detects_invalid_date(self):
        tickets, errors = tav.load_and_validate(self.tmp.name)
        # one row has invalid date (T5)
        self.assertTrue(any(e.get("ticket_id") == "T5" for e in errors))

    def test_load_and_validate_valid_count(self):
        tickets, errors = tav.load_and_validate(self.tmp.name)
        # 4 valid rows expected (T5 invalid)
        self.assertEqual(len(tickets), 4)

    def test_avg_resolution_by_priority(self):
        tickets, _ = tav.load_and_validate(self.tmp.name)
        avg = tav.avg_resolution_by_priority(tickets)
        # High has one resolved ticket with 1 day
        self.assertIn("High", avg)

    def test_tickets_open_more_than(self):
        tickets, _ = tav.load_and_validate(self.tmp.name)
        # create ticket with old created_date to simulate >7 days open
        old = {
            "ticket_id": "OLD",
            "customer_id": "C9",
            "subject": "old",
            "description": "old",
            "priority": "Low",
            "status": "Open",
            "created_date": tav.datetime.strptime("2024-01-01", tav.DATE_FMT).date(),
            "resolved_date": None,
            "assigned_to": "Agent_X",
        }
        tickets.append(old)
        long_open = tav.tickets_open_more_than(tickets, days=7)
        self.assertTrue(any(t["ticket_id"] == "OLD" for t in long_open))

    def test_most_common_subject_words(self):
        tickets, _ = tav.load_and_validate(self.tmp.name)
        words = tav.most_common_subject_words(tickets, topn=5)
        self.assertIsInstance(words, list)


if __name__ == "__main__":
    unittest.main()