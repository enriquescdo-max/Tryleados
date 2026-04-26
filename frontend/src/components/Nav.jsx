import { NavLink } from "react-router-dom";

export default function Nav() {
  const base = "px-4 py-2 text-sm font-medium rounded-lg transition-all";
  const active = `${base} bg-[#E05A1A] text-white`;
  const inactive = `${base} text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-gray-100`;

  return (
    <div className="flex items-center gap-2 px-6 py-2 bg-white border-b border-gray-100 sticky top-0 z-50">
      <div className="flex items-center gap-2 mr-auto">
        <div style={{ width: 22, height: 22, background: "#E05A1A", borderRadius: 5, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, fontWeight: 700, color: "#fff" }}>L</span>
        </div>
        <span className="font-semibold text-sm text-[#1A1A1A] tracking-tight">LeadOS</span>
      </div>

      <nav className="flex items-center gap-1">
        <NavLink to="/"       end className={({ isActive }) => isActive ? active : inactive}>Feed</NavLink>
        <NavLink to="/leads"     className={({ isActive }) => isActive ? active : inactive}>Lead Browser</NavLink>
        <NavLink to="/scorer"    className={({ isActive }) => isActive ? active : inactive}>Carrier Scorer</NavLink>
      </nav>
    </div>
  );
}
