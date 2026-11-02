import "./index.css";
import { useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Nav from "./components/Nav";
import Dashboard from "./pages/Dashboard";
import LeadBrowser from "./pages/LeadBrowser";
import CarrierScorer from "./pages/CarrierScorer";
import Campaigns from "./pages/Campaigns";
import ContentEngine from "./components/ContentEngine";
import LeadScout from "./pages/LeadScout";
import GetQuote from "./pages/GetQuote";
import Login from "./pages/Login";
import { getToken } from "./api";

export default function App() {
  const [authed, setAuthed] = useState(() => Boolean(getToken()));

  useEffect(() => {
    const onLogout = () => setAuthed(false);
    window.addEventListener("leados-unauthorized", onLogout);
    return () => window.removeEventListener("leados-unauthorized", onLogout);
  }, []);

  return (
    <Router>
      <Routes>
        <Route path="/quote" element={<GetQuote />} />
        <Route
          path="*"
          element={
            authed ? (
              <>
                <Nav />
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/leads" element={<LeadBrowser />} />
                  <Route path="/scorer" element={<CarrierScorer />} />
                  <Route path="/campaigns" element={<Campaigns />} />
                  <Route path="/content-engine" element={<ContentEngine />} />
                  <Route path="/leadscout" element={<LeadScout />} />
                </Routes>
              </>
            ) : (
              <Login onSuccess={() => setAuthed(true)} />
            )
          }
        />
      </Routes>
    </Router>
  );
}
