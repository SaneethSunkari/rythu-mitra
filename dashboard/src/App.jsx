import { useState, useEffect } from "react";
import LandingPage from "./components/LandingPage";
import AppShell from "./components/AppShell";
import BotView from "./components/BotView";
import DistrictView from "./components/DistrictView";
import MarketsView from "./components/MarketsView";
import dashboardData from "./data/dashboardData.json";

function getView() {
  const hash = window.location.hash;
  if (hash === "#app") return "app";
  if (hash === "#bot") return "bot";
  if (hash === "#district") return "district";
  if (hash === "#markets") return "markets";
  return "home";
}

export default function App() {
  const [view, setView] = useState(getView);
  const [siteData, setSiteData] = useState(dashboardData);

  useEffect(() => {
    const handleHash = () => {
      setView(getView());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadSiteContext() {
      try {
        const response = await fetch("/api/site/context");
        if (!response.ok) {
          throw new Error(`site context failed: ${response.status}`);
        }
        const payload = await response.json();
        if (!cancelled) {
          setSiteData(payload);
        }
      } catch (_err) {
        if (!cancelled) {
          setSiteData(dashboardData);
        }
      }
    }

    loadSiteContext();
    return () => {
      cancelled = true;
    };
  }, []);

  function openApp() {
    window.location.hash = "#app";
    window.scrollTo(0, 0);
  }

  function openBot() {
    window.location.hash = "#bot";
    window.scrollTo(0, 0);
  }

  function openDistrict() {
    window.location.hash = "#district";
    window.scrollTo(0, 0);
  }

  function openMarkets() {
    window.location.hash = "#markets";
    window.scrollTo(0, 0);
  }

  function goHome() {
    window.location.hash = "";
    window.scrollTo(0, 0);
  }

  if (view === "app") return <AppShell data={siteData} onGoHome={goHome} onOpenDistrict={openDistrict} onOpenMarkets={openMarkets} />;
  if (view === "bot") return <BotView data={siteData} onGoHome={goHome} />;
  if (view === "district") return <DistrictView data={siteData} onGoHome={goHome} onGoApp={openApp} onGoMarkets={openMarkets} />;
  if (view === "markets") return <MarketsView data={siteData} onGoHome={goHome} onGoApp={openApp} onGoDistrict={openDistrict} />;
  return <LandingPage data={siteData} onOpenApp={openApp} onOpenBot={openBot} />;
}
