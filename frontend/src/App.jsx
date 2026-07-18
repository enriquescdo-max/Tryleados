import "./index.css";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Nav from "./components/Nav";
import Dashboard from "./pages/Dashboard";
import LeadBrowser from "./pages/LeadBrowser";
import CarrierScorer from "./pages/CarrierScorer";
import Campaigns from "./pages/Campaigns";
import ContentEngine from "./components/ContentEngine";
import LeadScout from "./pages/LeadScout";
import GetQuote from "./pages/GetQuote";

export default function App() {
  return (
    <Router>
      <Nav />
      <Routes>
        <Route path="/"         element={<Dashboard />} />
        <Route path="/leads"    element={<LeadBrowser />} />
        <Route path="/scorer"   element={<CarrierScorer />} />
        <Route path="/campaigns" element={<Campaigns />} />
        <Route path="/content-engine" element={<ContentEngine />} />
        <Route path="/leadscout" element={<LeadScout />} />
        <Route path="/quote" element={<GetQuote />} />
      </Routes>
    </Router>
  );
}
