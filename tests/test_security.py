"""Auth, RLS migration, consent gates, and webhook signatures."""

import os
import unittest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "dummy")
os.environ.setdefault("SUPABASE_KEY", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
os.environ["LEADOS_OWNER_EMAIL"] = "owner@example.com"
os.environ["LEADOS_SESSION_SECRET"] = "unit-test-session-secret"
os.environ["VAPI_WEBHOOK_SECRET"] = "unit-test-vapi-secret"
os.environ.pop("AUTO_OUTREACH_ENABLED", None)
os.environ.pop("ENABLE_AUTO_OUTREACH", None)
os.environ.pop("AI_OUTBOUND_CALLS_ENABLED", None)
os.environ.pop("OUTBOUND_SEND_ENABLED", None)

from core.compliance import contact_decision
from core.owner_auth import authenticate, hash_password, issue_token, verify_password, verify_token

os.environ["LEADOS_OWNER_PASSWORD_HASH"] = hash_password("correct-horse-battery")

from fastapi.testclient import TestClient

import main


ROOT = os.path.join(os.path.dirname(__file__), "..")


class AuthTests(unittest.TestCase):
    def test_password_roundtrip(self):
        stored = hash_password("s3cret-value")
        self.assertTrue(verify_password("s3cret-value", stored))
        self.assertFalse(verify_password("wrong", stored))

    def test_authenticate_requires_config_and_correct_password(self):
        self.assertTrue(authenticate("owner@example.com", "correct-horse-battery"))
        self.assertFalse(authenticate("owner@example.com", "nope"))
        self.assertFalse(authenticate("other@example.com", "correct-horse-battery"))

    def test_missing_env_does_not_authenticate(self):
        saved = os.environ.pop("LEADOS_OWNER_PASSWORD_HASH")
        try:
            self.assertFalse(authenticate("owner@example.com", "correct-horse-battery"))
        finally:
            os.environ["LEADOS_OWNER_PASSWORD_HASH"] = saved

    def test_token_roundtrip_and_tamper_and_expiry(self):
        token = issue_token("owner@example.com", now=1_700_000_000)
        payload = verify_token(token, now=1_700_000_000 + 10)
        self.assertEqual(payload["sub"], "owner@example.com")
        self.assertIsNone(verify_token(token + "x", now=1_700_000_000 + 10))
        self.assertIsNone(verify_token(token, now=1_700_000_000 + 13 * 3600))
        body, sig = token.split(".", 1)
        self.assertIsNone(verify_token(body + ".AAAA", now=1_700_000_000))


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(main.app)

    def _login(self):
        res = self.client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "correct-horse-battery"},
        )
        self.assertEqual(res.status_code, 200, res.text)
        return {"Authorization": f"Bearer {res.json()['token']}"}

    def test_health_is_public(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_lead_and_admin_routes_require_owner(self):
        self.assertEqual(self.client.get("/api/leads").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/campaigns").status_code, 401)
        res = self.client.post("/api/v1/outreach/bulk", json={"leads": [], "channels": ["email"]})
        self.assertEqual(res.status_code, 401)
        auth = self._login()
        self.assertEqual(self.client.get("/api/leads", headers=auth).status_code, 200)
        self.assertEqual(
            self.client.post(
                "/api/auth/login",
                json={"email": "owner@example.com", "password": "wrong"},
            ).status_code,
            401,
        )

    def test_bulk_does_not_send(self):
        auth = self._login()
        res = self.client.post(
            "/api/v1/outreach/bulk",
            headers=auth,
            json={"leads": [{"raw_name": "Pat", "phone": "+15125550100"}], "channels": ["call", "email"]},
        )
        self.assertEqual(res.status_code, 403, res.text)
        self.assertIn("Bulk send", res.json()["detail"])

    def test_vapi_webhook_secret(self):
        os.environ["VAPI_WEBHOOK_SECRET"] = "unit-test-vapi-secret"
        body = {"message": {"type": "status-update"}}
        missing = self.client.post("/webhook/vapi", json=body)
        self.assertEqual(missing.status_code, 401)
        wrong = self.client.post("/webhook/vapi", json=body, headers={"X-Vapi-Secret": "nope"})
        self.assertEqual(wrong.status_code, 401)
        ok = self.client.post("/webhook/vapi", json=body, headers={"X-Vapi-Secret": "unit-test-vapi-secret"})
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertNotEqual(ok.status_code, 401)


class MigrationTests(unittest.TestCase):
    def test_new_migration_locks_leads_without_editing_002(self):
        with open(os.path.join(ROOT, "db/migrations/002_insurance_columns.sql"), encoding="utf-8") as handle:
            old = handle.read()
        with open(os.path.join(ROOT, "db/migrations/003_rls_owner_lockdown.sql"), encoding="utf-8") as handle:
            new = handle.read()
        self.assertIn("GRANT ALL ON leads TO anon", old)
        self.assertIn("DISABLE ROW LEVEL SECURITY", old)
        self.assertIn("ENABLE ROW LEVEL SECURITY", new.upper())
        self.assertIn("FORCE ROW LEVEL SECURITY", new.upper())
        self.assertIn("current_user_is_owner", new)
        self.assertIn("revoke all on table public.leads from anon", new.lower())
        self.assertNotIn("DISABLE ROW LEVEL SECURITY", new.upper())
        self.assertNotIn("GRANT ALL ON leads TO anon", new)


class ConsentTests(unittest.TestCase):
    def test_ai_call_stays_off_even_with_written_consent(self):
        written = [{"channel": "call", "source": "web_form", "written": True, "revoked_at": None}]
        decision = contact_decision(channel="ai_call", consents=written)
        self.assertFalse(decision.allowed)
        self.assertIn("off", decision.reason.lower())

    def test_sms_requires_written_consent(self):
        os.environ["OUTBOUND_SEND_ENABLED"] = "true"
        try:
            verbal = [{"channel": "sms", "source": "call", "written": False}]
            self.assertFalse(contact_decision(channel="sms", consents=verbal).allowed)
            written = [{"channel": "sms", "source": "web_form", "written": True}]
            self.assertTrue(contact_decision(channel="sms", consents=written).allowed)
        finally:
            os.environ.pop("OUTBOUND_SEND_ENABLED", None)

    def test_owner_callback_allows_call_consent_and_does_not_dial(self):
        consent = [{"channel": "call", "source": "call", "written": False, "scope": "owner_callback"}]
        decision = contact_decision(channel="owner_callback", consents=consent)
        self.assertTrue(decision.allowed)
        self.assertIn("owner", decision.reason.lower())
        self.assertFalse(contact_decision(channel="owner_callback", consents=[]).allowed)


if __name__ == "__main__":
    unittest.main()
