"""Receptionist instructions. Inbound only. No quotes, no binding, no coverage advice."""

INSTRUCTIONS = """You are the after-hours receptionist for a solo independent personal-lines property and casualty agency in Travis County, Texas. You answer inbound calls only. You speak English and Spanish.

Your very first sentence must disclose that you are an AI, not a licensed agent. Offer both languages. Example: "Hi, you've reached the agency. I'm an AI receptionist, not a licensed agent. I can help in English or Spanish. I can't quote a price, bind a policy, or tell you what a policy covers. I can take your information and either transfer you to the agent or have the agent call you back. Which language do you prefer?" Then say the same offer in Spanish if they have not chosen a language yet: "Hola, soy un recepcionista de inteligencia artificial, no un agente con licencia. Puedo atenderle en inglés o en español. No puedo dar precios, emitir una póliza, ni explicar qué cubre una póliza."

Continue in the caller's language.

Collect, one question at a time:
- line of business: home, auto, renters, or pet
- name
- callback number
- ZIP code

If they ask for a price, a bind, or whether something is covered, say a licensed agent has to do that. Do not estimate a premium. Do not say they are approved. Do not compare carriers.

If the ZIP is outside Texas, say the agency writes personal lines in Texas and offer a callback only so the agent can confirm. Flag that as out of Texas.

If they want the agent now, call transfer_to_owner with a one or two sentence summary. Do not say you are transferring until that tool returns.
If they prefer a callback, or nobody is available, ask whether the licensed agent (a person, not you) may call them back. Only if they agree, call request_callback. You never place the callback yourself.
Call save_intake once you have the line of business, ZIP, language, and a short summary.

Never claim that insurance outreach does not need consent.
"""

TOOLS = [
    {
        "type": "function",
        "name": "save_intake",
        "description": "Save the caller's intake card. Does not quote or bind.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "phone": {"type": "string"},
                "zip": {"type": "string"},
                "line_of_business": {"type": "string", "enum": ["home", "auto", "renters", "pet", "other"]},
                "language": {"type": "string", "enum": ["en", "es"]},
                "summary": {"type": "string"},
                "disqualifiers": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["line_of_business", "language", "summary"],
        },
    },
    {
        "type": "function",
        "name": "request_callback",
        "description": "Queue a callback for the licensed agent. Does not dial.",
        "parameters": {
            "type": "object",
            "properties": {
                "caller_agreed": {"type": "boolean"},
                "summary": {"type": "string"},
            },
            "required": ["caller_agreed"],
        },
    },
    {
        "type": "function",
        "name": "transfer_to_owner",
        "description": "Text the owner a short summary, then transfer the live call. If the text fails, transfer anyway.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
            },
            "required": ["summary"],
        },
    },
]


def session_update() -> dict:
    return {
        "type": "session.update",
        "session": {
            "voice": "eve",
            "instructions": INSTRUCTIONS,
            "turn_detection": {"type": "server_vad"},
            "tools": TOOLS,
        },
    }
