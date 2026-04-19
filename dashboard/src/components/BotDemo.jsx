import { useState } from "react";

function money(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function BotDemo({ scenarios }) {
  const [selectedId, setSelectedId] = useState(scenarios[0]?.id);
  const scenario = scenarios.find((item) => item.id === selectedId) ?? scenarios[0];

  return (
    <section className="section-card">
      <div className="section-card__header">
        <div>
          <span className="eyebrow eyebrow--small">WhatsApp walkthrough</span>
          <h2>Bot demo with visible reasoning</h2>
          <p>
            This panel turns the invisible part of the bot into something you
            can inspect: which farmer profile was assumed, what the filter path
            looked like, and what Telugu message the user would actually hear.
          </p>
        </div>
      </div>

      <div className="scenario-switcher">
        {scenarios.map((item) => (
          <button
            type="button"
            key={item.id}
            className={`scenario-button ${item.id === scenario.id ? "scenario-button--active" : ""}`}
            onClick={() => setSelectedId(item.id)}
          >
            {item.title}
          </button>
        ))}
      </div>

      <div className="bot-layout">
        <article className="bot-panel">
          <div className="bot-panel__header">
            <h3>Farmer profile</h3>
            <div className="profile-grid">
              <div>
                <span>Mandal</span>
                <strong>{scenario.profile.mandal}</strong>
              </div>
              <div>
                <span>Acres</span>
                <strong>{scenario.profile.acres}</strong>
              </div>
              <div>
                <span>Soil</span>
                <strong>{scenario.profile.soilZone}</strong>
              </div>
              <div>
                <span>Water</span>
                <strong>{scenario.profile.waterSource}</strong>
              </div>
              <div>
                <span>Loan</span>
                <strong>{money(scenario.profile.loanBurden)}</strong>
              </div>
              <div>
                <span>History</span>
                <strong>{scenario.profile.lastCrops.join(", ")}</strong>
              </div>
            </div>
          </div>

          <div className="conversation">
            {scenario.conversation.map((message, index) => (
              <div
                key={`${message.speaker}-${index}`}
                className={`bubble ${message.speaker === "farmer" ? "bubble--farmer" : "bubble--bot"}`}
              >
                <span className="bubble__speaker">
                  {message.speaker === "farmer" ? "Farmer" : "Bot"}
                </span>
                <p>{message.text}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="bot-panel">
          <div className="bot-picks">
            <div className="pick-banner">
              <span>Top pick</span>
              <strong>{scenario.topPick?.name ?? "No safe pick"}</strong>
              <small>{scenario.topPick?.teluguName ?? "fallback to advisory"}</small>
            </div>
            <div className="pick-banner pick-banner--soft">
              <span>Second option</span>
              <strong>{scenario.secondPick?.name ?? "No second option"}</strong>
              <small>{scenario.secondPick?.teluguName ?? "—"}</small>
            </div>
          </div>

          <div className="trace-list">
            {scenario.filterTrace.map((step) => (
              <article className="trace-card" key={step.id}>
                <div className="trace-card__top">
                  <strong>{step.title}</strong>
                  <span>
                    kept {step.kept} • removed {step.removed}
                  </span>
                </div>
                <p>{step.note}</p>
                <div className="trace-card__chips">
                  {step.highlights.map((item) => (
                    <span className="mini-chip" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>

          <div className="reply-card">
            <h3>Final Telugu reply</h3>
            <pre>{scenario.teluguReply}</pre>
          </div>
        </article>
      </div>
    </section>
  );
}
