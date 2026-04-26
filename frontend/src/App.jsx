import "./index.css";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Nav from "./components/Nav";
import Dashboard from "./pages/Dashboard";
import LeadBrowser from "./pages/LeadBrowser";
import CarrierScorer from "./pages/CarrierScorer";
import Campaigns from "./pages/Campaigns";

export default function App() {
  return (
    <Router>
      <Nav />
      <Routes>
        <Route path="/"         element={<Dashboard />} />
        <Route path="/leads"    element={<LeadBrowser />} />
        <Route path="/scorer"   element={<CarrierScorer />} />
        <Route path="/campaigns" element={<Campaigns />} />
      </Routes>
    </Router>
  );
}
