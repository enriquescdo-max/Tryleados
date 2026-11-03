"""Consent ledger, intake, SLA, drafts, and metrics. No network and no dialing."""

import os
import unittest
from datetime import timedelta

os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "dummy"
os.environ["SUPABASE_KEY"] = "dummy"
os.environ["ANTHROPIC_API_KEY"] = "dummy"
os.environ["LEADOS_STORE"] = "memory"
os.environ["LEADOS_OWNER_EMAIL"] = "owner@example.com"
os.environ["LEADOS_SESSION_SECRET"] = "phase1-session-secret"
os.environ["VAPI_WEBHOOK_SECRET"] = "phase1-vapi-secret"
os.environ["VOICE_BRIDGE_WEBHOOK_SECRET"] = "phase1-bridge-secret"
os.environ.pop("OUTBOUND_SEND_ENABLED", None)
os.environ.pop("AI_OUTBOUND_CALLS_ENABLED", None)

from core.owner_auth import hash_password

os.environ["LEADOS_OWNER_PASSWORD_HASH"] = hash_password("correct-horse-battery")

from fastapi.testclient import TestClient

import main
from services.agency_store import MEMORY, evaluate_sla, utcnow
from routers.voice_intake import run_sla_check


class VoicePhaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)

    def setUp(self):
        MEMORY.reset()
        os.environ["LEADOS_STORE"] = "memory"
        os.environ["SPEED_TO_LEAD_MINUTES"] = "5"

    def _auth(self):
        res = self.client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "correct-horse-battery"},
        )
        self.assertEqual(res.status_code, 200, res.text)
        return {"Authorization": f"Bearer {res.json()['token']}"}

    def test_voice_intake_requires_secret_and_shows_up_for_the_owner(self):
        payload = {
            "call_id": "call-abc",
            "name": "Maria Gonzalez",
            "phone": "+15125550111",
            "zip": "78704",
            "language": "es",
            "line_of_business": "renters",
            "summary": "New lease in Travis County. Wants a callback.",
            "callback_requested": True,
            "callback_consent": True,
            "consent_text": "Caller agreed the licensed agent may call them back.",
        }
        missing = self.client.post("/webhook/voice-intake", json=payload)
        self.assertEqual(missing.status_code, 401)

        saved = self.client.post(
            "/webhook/voice-intake",
            json=payload,
            headers={"X-Voice-Bridge-Secret": "phase1-bridge-secret"},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        auth = self._auth()
        leads = self.client.get("/api/leads", headers=auth)
        self.assertEqual(leads.status_code, 200, leads.text)
        names = [row.get("raw_name") for row in leads.json()["leads"]]
        self.assertIn("Maria Gonzalez", names)
        callbacks = self.client.get("/api/callbacks", headers=auth)
        self.assertEqual(callbacks.status_code, 200)
        self.assertEqual(callbacks.json()["count"], 1)

    def test_callback_queue_hides_leads_without_consent(self):
        self.client.post(
            "/webhook/voice-intake",
            json={
                "call_id": "call-no",
                "name": "No Consent",
                "phone": "+15125550222",
                "zip": "78701",
                "line_of_business": "auto",
                "summary": "Asked for a price. No callback agreement.",
                "callback_requested": True,
                "callback_consent": False,
            },
            headers={"X-Voice-Bridge-Secret": "phase1-bridge-secret"},
        )
        auth = self._auth()
        callbacks = self.client.get("/api/callbacks", headers=auth)
        self.assertEqual(callbacks.json()["count"], 0)
        self.assertEqual(self.client.get("/api/callbacks").status_code, 401)

    def test_out_of_texas_is_flagged(self):
        saved = self.client.post(
            "/webhook/voice-intake",
            json={
                "call_id": "call-ca",
                "name": "Sam",
                "phone": "+14155550100",
                "zip": "94107",
                "line_of_business": "home",
                "summary": "Calling from California.",
                "callback_consent": True,
            },
            headers={"X-Voice-Bridge-Secret": "phase1-bridge-secret"},
        )
        self.assertIn("out_of_texas", saved.json()["disqualifiers"])

    def test_sla_alerts_the_owner_once(self):
        self.client.post(
            "/webhook/voice-intake",
            json={
                "call_id": "call-sla",
                "name": "Late",
                "phone": "+15125550333",
                "zip": "78702",
                "line_of_business": "pet",
                "summary": "Pet intake.",
                "callback_consent": True,
            },
            headers={"X-Voice-Bridge-Secret": "phase1-bridge-secret"},
        )
        notes = []

        def notifier(lead):
            notes.append(lead["id"])
            self.assertNotEqual(lead.get("phone"), os.getenv("OWNER_ALERT_PHONE"))

        started = utcnow()
        self.assertEqual(evaluate_sla(MEMORY, started, notifier), [])
        later = started + timedelta(minutes=6)
        first = run_sla_check(later, notifier)
        self.assertEqual(len(first), 1)
        second = run_sla_check(later + timedelta(minutes=1), notifier)
        self.assertEqual(second, [])
        self.assertEqual(len(notes), 1)

    def test_followup_approval_does_not_send(self):
        saved = self.client.post(
            "/webhook/voice-intake",
            json={
                "call_id": "call-draft",
                "name": "Alex",
                "phone": "+15125550444",
                "zip": "78745",
                "line_of_business": "home",
                "summary": "Home question.",
                "callback_consent": True,
            },
            headers={"X-Voice-Bridge-Secret": "phase1-bridge-secret"},
        )
        lead_id = saved.json()["lead_id"]
        auth = self._auth()
        draft = self.client.post(f"/api/leads/{lead_id}/followups", headers=auth)
        self.assertEqual(draft.status_code, 200, draft.text)
        self.assertFalse(draft.json()["sent"])
        self.assertNotIn("no consent", draft.json()["body"].lower())
        approved = self.client.post(
            f"/api/leads/{lead_id}/followups/{draft.json()['id']}/approve",
            headers=auth,
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["status"], "approved")
        self.assertFalse(approved.json()["sent"])
        sent = self.client.post(
            f"/api/leads/{lead_id}/followups/{draft.json()['id']}/send",
            headers=auth,
        )
        self.assertEqual(sent.status_code, 403)

    def test_metrics_csv_and_web_consent(self):
        form = self.client.post("/api/public/web-lead", json={
            "first_name": "Riley",
            "last_name": "Nguyen",
            "phone": "+15125550555",
            "zip": "78703",
            "email": "riley@example.com",
            "insurance_types": ["auto"],
            "tcpa_consent": True,
            "consent_text": "I agree to be contacted by a licensed agent by phone or text.",
        })
        self.assertEqual(form.status_code, 200, form.text)
        refused = self.client.post("/api/public/web-lead", json={
            "first_name": "No",
            "phone": "+15125550666",
            "tcpa_consent": False,
        })
        self.assertEqual(refused.status_code, 400)
        auth = self._auth()
        metrics = self.client.get("/api/metrics", headers=auth)
        self.assertEqual(metrics.status_code, 200, metrics.text)
        self.assertGreaterEqual(metrics.json()["leads"], 1)
        self.assertGreater(metrics.json()["consent_rate"], 0)
        csv_res = self.client.get("/api/metrics/export.csv", headers=auth)
        self.assertEqual(csv_res.status_code, 200, csv_res.text)
        self.assertTrue(csv_res.text.splitlines()[0].startswith("calls,leads,median_response_seconds,consent_rate"))
        self.assertEqual(self.client.get("/api/metrics/export.csv").status_code, 401)

    def test_migration_004_enables_rls_and_does_not_grant_anon(self):
        path = os.path.join(os.path.dirname(__file__), "..", "db/migrations/004_voice_consent_intake.sql")
        with open(path, encoding="utf-8") as handle:
            sql = handle.read()
        lowered = sql.lower()
        self.assertIn("enable row level security", lowered)
        self.assertIn("force row level security", lowered)
        self.assertIn("revoke all on table public.consent_ledger from anon", lowered)
        self.assertNotIn("disable row level security", lowered)
        self.assertNotIn("grant all", lowered)
        self.assertNotIn("to anon", lowered)


if __name__ == "__main__":
    unittest.main()
