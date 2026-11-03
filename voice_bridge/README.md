# LeadOS voice bridge

Inbound receptionist for the Travis County personal-lines agency. Callers reach a Twilio number. Twilio sends the call over SIP to xAI. xAI runs Grok Voice 3 and posts `realtime.call.incoming` here. This process joins the call, follows the receptionist script, and writes an intake card into tryleadOS.

It does not place outbound calls. It does not quote, bind, or explain coverage. The only text it sends is a short summary to the owner's own phone, immediately before a transfer. If that text fails, the transfer still happens. That is the blind transfer.

Nothing in this repository deploys the bridge or places a call. You deploy it yourself when the checklist below is done.

## How a call moves

1. A person calls your Twilio number.
2. The Twilio Elastic SIP trunk originates to `sip:{your-registered-number}@sip.voice.x.ai;transport=tls`.
3. xAI accepts the SIP call and POSTs a signed `realtime.call.incoming` event to `https://<fly-app>/webhooks/xai`.
4. This service checks the Standard Webhooks signature (`webhook-id`, `webhook-timestamp`, `webhook-signature`).
5. Test mode is on by default. If the caller is not on `VOICE_ALLOWLIST`, the service hangs up and does not start the agent.
6. Otherwise it opens `wss://api.x.ai/v1/realtime?call_id={call_id}` with your xAI API key, sends `session.update` (voice `eve`, model `grok-voice-3.0`), then `response.create`.
7. The model may call `save_intake`, `request_callback`, or `transfer_to_owner`.
8. `save_intake` and an agreed callback POST to `{LEADOS_API_URL}/webhook/voice-intake` with `X-Voice-Bridge-Secret`.
9. `transfer_to_owner` texts `OWNER_ALERT_PHONE` first, then `POST /v1/realtime/calls/{call_id}/refer` with `tel:{OWNER_PHONE}`.

## Test mode

`VOICE_TEST_MODE` defaults to `true`. Leave it on until your own phone is in `VOICE_ALLOWLIST` and you have placed one test call. An empty allowlist rejects every caller.

## Environment

Copy `.env.example`. Every credential is an environment variable. None are baked into the image.

| Name | Purpose |
| --- | --- |
| `XAI_API_KEY` | Server-side key. Join the realtime socket and refer or hang up. |
| `XAI_WEBHOOK_SECRET` | Signing secret xAI shows once when you register the number. |
| `XAI_VOICE_MODEL` | `grok-voice-3.0` |
| `VOICE_TEST_MODE` | `true` until you are ready |
| `VOICE_ALLOWLIST` | Comma-separated E.164 numbers that may call while test mode is on |
| `OWNER_PHONE` | Where a live transfer is referred |
| `OWNER_ALERT_PHONE` | Your cell. The pre-transfer summary goes here, never to the caller as marketing. |
| `TWILIO_ACCOUNT_SID` | Twilio REST, only for that owner summary |
| `TWILIO_AUTH_TOKEN` | Twilio REST |
| `TWILIO_FROM_NUMBER` | A number you own, used as the From on the owner summary |
| `LEADOS_API_URL` | Railway base URL, no trailing path |
| `VOICE_BRIDGE_WEBHOOK_SECRET` | Same value as on Railway |

Enable Zero Data Retention on the xAI account before any caller who is not you reaches this number. This service does not store call audio.

## Twilio

1. Buy or choose the inbound number.
2. Voice → Elastic SIP Trunking → create a trunk.
3. Origination URI: `sip:{number}@sip.voice.x.ai;transport=tls`. `{number}` is the Direct SIP number you registered with xAI, in E.164.
4. Assign the Twilio number to that trunk.
5. Turn on call transfer so a mid-call REFER is allowed.

10DLC is the US registration for application-to-person texting campaigns. This bridge does not text scraped people and does not run a marketing campaign. Its only SMS is the transfer summary to your own phone. Register 10DLC later if you separately decide to text customers, and only after written consent is on file in tryleadOS.

## xAI

1. Turn on Zero Data Retention for the account.
2. Create an API key.
3. Register the number as a bring-your-own trunk (`origin: byo_trunk`) and set the webhook URL to `https://<this-fly-app>/webhooks/xai`.
4. Copy the signing secret into `XAI_WEBHOOK_SECRET`. xAI returns it once.

## Fly.io

From this directory, when you are ready:

```bash
fly launch --no-deploy
fly secrets set XAI_API_KEY=... XAI_WEBHOOK_SECRET=... VOICE_TEST_MODE=true VOICE_ALLOWLIST=+1... OWNER_PHONE=+1... OWNER_ALERT_PHONE=+1... TWILIO_ACCOUNT_SID=... TWILIO_AUTH_TOKEN=... TWILIO_FROM_NUMBER=+1... LEADOS_API_URL=https://... VOICE_BRIDGE_WEBHOOK_SECRET=...
fly deploy
```

`fly.toml` listens on port 8080 and checks `GET /health`. Do not put secrets in `fly.toml`.

## Railway

Set `VOICE_BRIDGE_WEBHOOK_SECRET` to the same value, `LEADOS_STORE=supabase`, and `SPEED_TO_LEAD_MINUTES=5`. Run migration `004_voice_consent_intake.sql` after `003`. AI outbound stays off.
