"""Voice bridge unit tests. No network."""

import base64
import json
import os
import time
import unittest

os.environ["VOICE_TEST_MODE"] = "true"
os.environ["VOICE_ALLOWLIST"] = ""
os.environ["XAI_WEBHOOK_SECRET"] = "whsec_" + base64.b64encode(b"test-secret-key").decode()
os.environ["OWNER_PHONE"] = "+15125550199"

from fastapi.testclient import TestClient

from voice_bridge.app import BridgeDeps, app, set_deps
from voice_bridge.calls import build_session, caller_allowed, extract_caller, transfer_to_owner
from voice_bridge.script import INSTRUCTIONS, TOOLS
from voice_bridge.signatures import expected_signature, verify_webhook


SECRET = os.environ["XAI_WEBHOOK_SECRET"]


def _signed(body: bytes, timestamp: str | None = None):
    if timestamp is None:
        timestamp = str(int(time.time()))
    signature = "v1," + expected_signature(SECRET, "msg_1", timestamp, body)
    return {
        "webhook-id": "msg_1",
        "webhook-timestamp": timestamp,
        "webhook-signature": signature,
        "content-type": "application/json",
    }


class SignatureTests(unittest.TestCase):
    def test_accepts_a_good_signature_and_rejects_bad_or_stale(self):
        body = b'{"type":"realtime.call.incoming"}'
        headers = _signed(body, "1700000000")
        self.assertTrue(verify_webhook(SECRET, headers, body, now=1700000000))
        bad = dict(headers)
        bad["webhook-signature"] = "v1,AAAA"
        self.assertFalse(verify_webhook(SECRET, bad, body, now=1700000000))
        self.assertFalse(verify_webhook(SECRET, headers, body, now=1700000000 + 1000))
        self.assertFalse(verify_webhook("", headers, body, now=1700000000))


class CallPlanTests(unittest.IsolatedAsyncioTestCase):
    def test_test_mode_rejects_unknown_callers(self):
        os.environ["VOICE_TEST_MODE"] = "true"
        os.environ["VOICE_ALLOWLIST"] = "+15125550100"
        self.assertFalse(caller_allowed("+15125550999"))
        self.assertTrue(caller_allowed("+1 (512) 555-0100"))
        os.environ["VOICE_ALLOWLIST"] = ""
        self.assertFalse(caller_allowed("+15125550100"))

    def test_session_discloses_ai_and_has_no_quote_tool(self):
        session = build_session("call-1")
        instructions = session["session_update"]["session"]["instructions"]
        names = [tool["name"] for tool in session["session_update"]["session"]["tools"]]
        self.assertIn("AI receptionist", instructions)
        self.assertIn("Spanish", instructions)
        self.assertIn("can't quote", instructions.lower())
        self.assertNotIn("quote_price", names)
        self.assertNotIn("bind_policy", names)
        self.assertEqual(names, ["save_intake", "request_callback", "transfer_to_owner"])
        self.assertIn("AI", INSTRUCTIONS)
        self.assertTrue(all("quote" not in tool["name"] and "bind" not in tool["name"] for tool in TOOLS))

    async def test_transfer_texts_before_refer_and_still_refers_if_text_fails(self):
        order = []

        async def sms(summary):
            order.append(("sms", summary))
            return True

        async def refer(call_id, target):
            order.append(("refer", call_id, target))

        result = await transfer_to_owner("call-1", "Home, 78704, Maria", sms, refer)
        self.assertEqual(order[0][0], "sms")
        self.assertEqual(order[1][0], "refer")
        self.assertEqual(result["transfer"], "summary")
        self.assertEqual(result["target_uri"], "tel:+15125550199")

        order.clear()

        async def sms_fails(summary):
            order.append("sms")
            raise RuntimeError("twilio down")

        async def refer2(call_id, target):
            order.append("refer")

        result = await transfer_to_owner("call-2", "blind", sms_fails, refer2)
        self.assertEqual(order, ["sms", "refer"])
        self.assertEqual(result["transfer"], "blind")
        self.assertFalse(result["sms_sent"])


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.hung = []
        self.started = []

        async def hangup(call_id):
            self.hung.append(call_id)

        async def start_session(call_id, caller):
            self.started.append((call_id, caller))
            return build_session(call_id)

        set_deps(BridgeDeps(hangup, start_session, SECRET))
        self.client = TestClient(app)
        os.environ["VOICE_TEST_MODE"] = "true"
        os.environ["VOICE_ALLOWLIST"] = "+15125550100"

    def _event(self, caller):
        body = {
            "type": "realtime.call.incoming",
            "data": {
                "call_id": "00000000-0000-0000-0000-000000000001",
                "sip_headers": [{"name": "From", "value": f'"Caller" <sip:{caller}@twilio.com>'}],
            },
        }
        raw = json.dumps(body).encode()
        return raw, _signed(raw)

    def test_bad_signature_is_401(self):
        raw, headers = self._event("+15125550100")
        headers["webhook-signature"] = "v1,nope"
        res = self.client.post("/webhooks/xai", content=raw, headers=headers)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(self.hung, [])
        self.assertEqual(self.started, [])

    def test_non_allowlisted_caller_hangs_up_without_a_session(self):
        raw, headers = self._event("+15125550999")
        res = self.client.post("/webhooks/xai", content=raw, headers=headers)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["disposition"], "rejected_test_mode")
        self.assertEqual(self.hung, ["00000000-0000-0000-0000-000000000001"])
        self.assertEqual(self.started, [])

    def test_allowlisted_caller_starts_a_session(self):
        raw, headers = self._event("+15125550100")
        caller = extract_caller(json.loads(raw))
        self.assertIn("5125550100", caller)
        res = self.client.post("/webhooks/xai", content=raw, headers=headers)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["disposition"], "accepted")
        self.assertEqual(self.hung, [])
        self.assertEqual(len(self.started), 1)


if __name__ == "__main__":
    unittest.main()
