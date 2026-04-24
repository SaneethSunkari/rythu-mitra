const coreFilters = [
  {
    number: "01",
    title: "Soil fit",
    body: "Rejects crops that do not match mandal-level soil reality before any price optimism enters the picture.",
  },
  {
    number: "02",
    title: "Water + weather",
    body: "Checks water source and live weather risk so a crop is not recommended just because it looks good on paper.",
  },
  {
    number: "03",
    title: "District pressure",
    body: "Tracks supply crowding and blocks the engine from pushing farmers into the same oversupplied lane.",
  },
  {
    number: "04",
    title: "Price range",
    body: "Uses floor, average, and ceiling ranges instead of pretending the model can promise one price.",
  },
  {
    number: "05",
    title: "Downside survivability",
    body: "Only keeps crops that still make sense under floor-price pressure and loan burden.",
  },
];

const faqItems = [
  {
    question: "Who is this for?",
    answer:
      "Farmers use the WhatsApp voice interface. This website is for anyone who needs to inspect, trust, or evaluate the system — families, advisors, buyers, recruiters.",
  },
  {
    question: "Is the analysis on this website the same as the WhatsApp bot?",
    answer:
      "Yes. The analysis tool calls the same engine that powers the WhatsApp assistant. There is no separate demo mode — every scenario runs through the real constraint pipeline.",
  },
  {
    question: "What makes this different from a normal agriculture dashboard?",
    answer:
      "Most dashboards show market data. Rythu Mitra adds a constraint engine that combines soil fit, water reality, district supply pressure, price ranges, and downside risk before it recommends anything.",
  },
  {
    question: "Why does the engine sometimes return no safe crop?",
    answer:
      "Because honesty is a feature. If no crop survives all five filters under the current district state, the engine says so rather than forcing a risky recommendation.",
  },
];

function formatUtcStamp(value) {
  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  });
}

export default function LandingPage({ data, onOpenApp, onOpenBot }) {
  const { summary, proofCards = [] } = data;

  return (
    <main className="site-shell">
      {/* ── Nav ── */}
      <nav className="nav">
        <div className="nav__logo">
          Rythu <span>Mitra</span>
        </div>
        <div className="nav__links">
          <a href="#how-it-works">How it works</a>
          <button type="button" className="nav__link-btn" onClick={onOpenBot}>WhatsApp</button>
          <a href="#faq">FAQ</a>
          <button type="button" className="btn btn--green btn--sm nav__cta" onClick={onOpenApp}>
            Open analysis tool
          </button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="hero">
        <div className="hero-centered">
          <div className="eyebrow-row">
            <span className="eyebrow">Rythu Mitra</span>
            <span className="eyebrow soft">Nizamabad · Telangana</span>
          </div>

          <h1 className="hero__title">
            A crop advisor built for <em>real uncertainty.</em>
          </h1>

          <p className="hero__sub">
            Small farmers send a Telugu voice note on WhatsApp and get a
            recommendation that accounts for soil, water, district supply
            crowding, price ranges, and downside risk — before anything is
            suggested.
          </p>

          <div className="hero-actions">
            <button type="button" className="btn btn--green btn--lg" onClick={onOpenApp}>
              Open analysis tool
            </button>
            <a href="#how-it-works" className="btn btn--ghost btn--lg">
              See how it works
            </a>
          </div>

          <div className="hero-trustbar">
            <span>{summary.mandalCount} mandals covered</span>
            <span>{summary.mandiCount} mandi price feeds</span>
            <span>5-filter constraint engine</span>
            <span>Telugu voice-first</span>
            <span>district supply tracking</span>
          </div>
        </div>
      </section>

      {/* ── Why it exists ── */}
      <section className="website-section" id="why">
        <div className="container">
          <div className="section-intro">
            <span className="eyebrow eyebrow--soft">The problem</span>
            <h2>Most crop advice is optimistic in the wrong direction.</h2>
            <p>
              Recommendations that ignore soil reality, district supply crowding,
              and what happens when prices fall don't protect farmers — they just
              sound helpful. Rythu Mitra is built around the constraint that an
              answer is only useful if it survives the downside.
            </p>
          </div>

          <div className="why-grid">
            <article className="why-card why-card--problem">
              <span className="micro-label">The gap</span>
              <h3>Advice without constraints</h3>
              <p>
                Standard advisory tells farmers which crops fetch the highest price
                today. It does not check whether that crop fits the soil, whether
                the local district is already oversupplied, or whether the farmer
                survives a bad season.
              </p>
            </article>
            <article className="why-card why-card--solution">
              <span className="micro-label">The approach</span>
              <h3>Five filters. Every crop survives all five.</h3>
              <p>
                Rythu Mitra runs each crop through soil fit, water reality,
                district supply pressure, price range, and downside survivability
                before anything reaches the farmer. If a crop fails any filter,
                it is removed — not downranked.
              </p>
            </article>
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="website-section website-section--contrast" id="how-it-works">
        <div className="container">
          <div className="section-intro">
            <span className="eyebrow eyebrow--soft">How it works</span>
            <h2>Five filters. Every recommendation survives all five.</h2>
            <p>
              No crop reaches the farmer unless it clears every constraint.
              That is what makes the answer safe instead of just optimistic.
            </p>
          </div>

          <div className="filter-rail">
            {coreFilters.map((filter) => (
              <article className="filter-rail__card" key={filter.number}>
                <span className="filter-rail__index">{filter.number}</span>
                <strong>{filter.title}</strong>
                <p>{filter.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── Two interfaces ── */}
      <section className="website-section">
        <div className="container">
          <div className="section-intro">
            <span className="eyebrow eyebrow--soft">Two interfaces</span>
            <h2>One engine. WhatsApp for farmers. Website for everyone else.</h2>
          </div>

          <div className="interface-grid">
            <article className="interface-card interface-card--farmer">
              <span className="micro-label">For farmers</span>
              <h3>WhatsApp bot</h3>
              <ul>
                <li>Telugu voice-first interaction</li>
                <li>3–4 message profile collection</li>
                <li>Warm, conversational reply style</li>
                <li>No app, no dashboard, no friction</li>
              </ul>
            </article>

            <article className="interface-card interface-card--public">
              <span className="micro-label">For advisors, evaluators, and buyers</span>
              <h3>This website</h3>
              <ul>
                <li>District pressure and open lanes visible</li>
                <li>Live trade board and weather stream</li>
                <li>Full filter trail and rejection reasons</li>
                <li>Same engine — run any scenario live</li>
              </ul>
            </article>
          </div>

          <div className="interface-cta">
            <button type="button" className="btn btn--green btn--lg" onClick={onOpenApp}>
              Open the analysis tool →
            </button>
          </div>
        </div>
      </section>

      {/* ── Stats ribbon ── */}
      <section className="website-section--tight">
        <div className="container signal-ribbon signal-ribbon--premium">
          <article className="signal-panel">
            <span className="micro-label">District coverage</span>
            <strong>{summary.mandalTopPickCount}/{summary.mandalCount}</strong>
            <p>Mandals currently yield a safe top pick under the district model.</p>
          </article>
          <article className="signal-panel">
            <span className="micro-label">Pressure ledger</span>
            <strong>{summary.oversuppliedCropCount}</strong>
            <p>Crop lanes are already under crowding stress and must be watched.</p>
          </article>
          <article className="signal-panel">
            <span className="micro-label">Market + weather</span>
            <strong>{summary.priceRowCount + summary.weatherDayCount}</strong>
            <p>Price rows and forecast windows visible on the same surface.</p>
          </article>
        </div>
      </section>

      {!!proofCards.length && (
        <section className="website-section website-section--tight">
          <div className="container">
            <div className="section-intro section-intro--compact">
              <span className="eyebrow eyebrow--soft">Explanation and proof</span>
              <h2>Why the answer can be trusted.</h2>
              <p>
                The home page keeps proof short. The analysis tool opens the full reasoning only when you want to inspect it.
              </p>
            </div>
            <div className="proof-strip">
              {proofCards.map((item) => (
                <article className="proof-card" key={item.title}>
                  <span className="micro-label">Proof layer</span>
                  <strong>{item.title}</strong>
                  <p>{item.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="website-section--tight">
        <div className="container signal-ribbon signal-ribbon--compact">
          <article className="signal-panel">
            <span className="micro-label">Mandi source</span>
            <strong>{summary.priceMode}</strong>
            <p>{summary.priceSourceLabel}</p>
          </article>
          <article className="signal-panel">
            <span className="micro-label">Weather source</span>
            <strong>{summary.weatherMode}</strong>
            <p>{summary.weatherSourceLabel}</p>
          </article>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="website-section website-section--contrast" id="faq">
        <div className="container faq-shell">
          <div className="section-intro">
            <span className="eyebrow eyebrow--soft">FAQ</span>
            <h2>Common questions answered directly.</h2>
          </div>
          <div className="faq-grid">
            {faqItems.map((item) => (
              <article className="faq-card" key={item.question}>
                <h3>{item.question}</h3>
                <p>{item.answer}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="site-footer">
        <div className="site-footer__inner">
          <span className="site-footer__logo">
            Rythu <span>Mitra</span>
          </span>
          <button type="button" className="btn btn--green btn--sm" onClick={onOpenApp}>
            Open analysis tool
          </button>
          <span className="site-footer__meta">
            Last export: {formatUtcStamp(summary.generatedAtUtc)} · Nizamabad, Telangana
          </span>
        </div>
      </footer>
    </main>
  );
}
