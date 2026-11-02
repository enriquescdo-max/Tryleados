import { useState } from "react";
import { apiFetch, setToken } from "../api";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Login({ onSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await apiFetch(`${API}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.token) {
        setError(data.detail || "Sign-in failed.");
        return;
      }
      setToken(data.token);
      onSuccess();
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F8F8F6] flex items-center justify-center px-6">
      <form onSubmit={submit} className="w-full max-w-sm bg-white border border-gray-100 rounded-[10px] p-8 shadow-sm">
        <h1 className="text-2xl text-[#1A1A1A] mb-1" style={{ fontFamily: "'Playfair Display', serif" }}>
          LeadOS
        </h1>
        <p className="text-sm text-[#6B6B6B] mb-6">Owner sign-in. This dashboard is not public.</p>
        <label className="block text-xs text-[#6B6B6B] mb-1">Email</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-4 px-3 py-2 border border-gray-200 rounded-[10px] text-sm"
        />
        <label className="block text-xs text-[#6B6B6B] mb-1">Password</label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-4 px-3 py-2 border border-gray-200 rounded-[10px] text-sm"
        />
        {error && <p className="text-sm text-[#E24B4A] mb-3">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full py-2.5 rounded-[10px] bg-[#00A86B] text-white text-sm font-semibold disabled:opacity-60"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
