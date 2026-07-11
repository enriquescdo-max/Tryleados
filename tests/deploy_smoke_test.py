#!/usr/bin/env python3
"""Deploy smoke tests — catches the exact bug class that silently broke every
Railway deploy for weeks: an unguarded router import raising ImportError, or
a router module with a plain SyntaxError, either of which crashes `main.py`
at import time with no visible error in the running app (Railway just falls
back to serving the last successful build). Run this before every deploy.
Exits 1 on failure."""
import ast
import os
import sys
import glob

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# main.py talks to Supabase/Anthropic at import time inside try/except blocks —
# give it harmless dummy credentials so those blocks exercise their real code
# path (and any real bug in them) instead of short-circuiting on a KeyError.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "dummy")
os.environ.setdefault("SUPABASE_KEY", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")

PASS = "\033[0;32m✓\033[0m"
FAIL = "\033[0;31m✗\033[0m"
failures: list[str] = []


def check(name: str, condition: bool, detail: str = ""):
    if condition:
        print(f"  {PASS} {name}")
    else:
        print(f"  {FAIL} {name}{' — ' + detail if detail else ''}")
        failures.append(name)


# ── every .py file the app can reach must at least parse ────────────────────

def test_no_syntax_errors():
    print("\n[syntax] Every module main.py can import must parse cleanly")
    paths = (
        glob.glob("*.py")
        + glob.glob("routers/*.py")
        + glob.glob("services/*.py")
        + glob.glob("agents/*.py")
        + glob.glob("core/*.py")
        + glob.glob("api/*.py")
    )
    for path in sorted(paths):
        try:
            ast.parse(open(path, encoding="utf-8").read(), filename=path)
            check(path, True)
        except SyntaxError as e:
            check(path, False, f"{e.__class__.__name__}: {e}")


# ── main.py must actually import without crashing ────────────────────────────

def test_main_imports_cleanly():
    print("\n[import] main.py boots without raising")
    try:
        import main  # noqa: F401
        check("import main", True)
        return main
    except Exception as e:
        check("import main", False, f"{e.__class__.__name__}: {e}")
        return None


# ── every router that's supposed to load actually loaded ────────────────────

def test_all_routers_loaded(main_module):
    print("\n[routers] Every router in main.py registered at least one route")
    if main_module is None:
        check("routers loaded", False, "main.py failed to import — skipping")
        return
    from fastapi.testclient import TestClient
    c = TestClient(main_module.app)
    spec = c.get("/openapi.json").json()
    paths = spec["paths"]
    expected_prefixes = [
        "/api/leads",
        "/api/v1/carrier-score",
        "/api/v1/campaigns",
        "/api/v1/outreach",
        "/webhook/vapi",
        "/agents/content-engine",
        "/agents",
    ]
    for prefix in expected_prefixes:
        found = any(p.startswith(prefix) for p in paths)
        check(f"a route under {prefix} exists", found, f"none of {len(paths)} paths matched")


# ── core endpoints actually respond ──────────────────────────────────────────

def test_core_endpoints(main_module):
    print("\n[endpoints] Core endpoints respond")
    if main_module is None:
        check("core endpoints", False, "main.py failed to import — skipping")
        return
    from fastapi.testclient import TestClient
    c = TestClient(main_module.app)

    r = c.get("/health")
    check("GET /health -> 200", r.status_code == 200, str(r.status_code))

    r = c.get("/")
    check("GET / -> 200", r.status_code == 200, str(r.status_code))

    r = c.get("/api/leads")
    check("GET /api/leads -> 200 (not 404)", r.status_code == 200, str(r.status_code))

    r = c.get("/api/leads/stats")
    check("GET /api/leads/stats -> 200 (not 404)", r.status_code == 200, str(r.status_code))


# ── CORS must allow the real production frontend and reject unknown ones ────

def test_cors(main_module):
    print("\n[cors] Production frontend is allowed, unknown origins are not")
    if main_module is None:
        check("cors", False, "main.py failed to import — skipping")
        return
    from fastapi.testclient import TestClient
    c = TestClient(main_module.app)

    allowed = ["https://tryleados.com", "http://localhost:5173"]
    for origin in allowed:
        r = c.get("/api/leads", headers={"Origin": origin})
        acao = r.headers.get("access-control-allow-origin")
        check(f"{origin} is allowed", acao == origin, f"got ACAO={acao!r}")

    r = c.get("/api/leads", headers={"Origin": "https://evil.example.com"})
    acao = r.headers.get("access-control-allow-origin")
    check("unknown origin is rejected", acao is None, f"got ACAO={acao!r}")


# ── main ──────────────────────────────────────────────────────────────────────

def run_all():
    print("\n\033[1;37m LeadOS Deploy Smoke Tests\033[0m")
    print("═" * 50)

    test_no_syntax_errors()
    main_module = test_main_imports_cleanly()
    test_all_routers_loaded(main_module)
    test_core_endpoints(main_module)
    test_cors(main_module)

    print("\n" + "═" * 50)
    if failures:
        print(f"\033[0;31m FAILED: {len(failures)} test(s)\033[0m")
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    else:
        print(f"\033[0;32m ALL TESTS PASSED\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    run_all()
