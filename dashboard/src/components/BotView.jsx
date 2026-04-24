import BotDemo from "./BotDemo";

export default function BotView({ data, onGoHome }) {
  const { demoScenarios } = data;

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <button type="button" className="app-nav__back" onClick={onGoHome}>
          ← Home
        </button>
        <div className="app-nav__logo">
          Rythu <span>Mitra</span>
        </div>
        <div className="app-nav__links">
          <span className="app-nav__label">WhatsApp bot walkthrough</span>
        </div>
      </nav>

      <section className="app-section">
        <div className="container">
          <BotDemo scenarios={demoScenarios} />
        </div>
      </section>
    </div>
  );
}
