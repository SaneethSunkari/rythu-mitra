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
    <section className="section-shell">
      <div className="section-heading">
        <div>
          <span className="eyebrow eyebrow--soft">Bot walkthrough</span>
          <h2>The field conversation, opened up for inspection</h2>
          <p>
            The voice and chat interface is only useful if the hidden reasoning
            stays auditable. This panel lets someone inspect the farmer
            assumption, the filter trail, the rejected crops, and the Telugu
            reply that would actually go out.
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

      <div className="demo-stage">
        <article className="panel phone-panel">
          <div className="phone-panel__chrome">
            <div className="phone-panel__camera" />
            <span>WhatsApp field conversation</span>
          </div>

          <div className="phone-panel__profile">
            <div>
              <span className="micro-label">Farmer profile</span>
              <strong>
                {scenario.profile.mandal} • {scenario.profile.acres} acres
              </strong>
            </div>
            <div>
              <span className="micro-label">Soil / water</span>
              <strong>
                {scenario.profile.soilZone} • {scenario.profile.waterSource}
              </strong>
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

        <div className="logic-column">
          <article className="panel decision-panel">
            <div className="decision-panel__top">
              <div>
                <span className="micro-label">Decision answer</span>
                <h3>
                  {scenario.topPick?.name ?? "No safe pick"} over{" "}
                  {scenario.secondPick?.name ?? "no second option"}
                </h3>
              </div>
              <div className="decision-pair">
                <div className="decision-pair__card">
                  <span className="micro-label">Top pick</span>
                  <strong>{scenario.topPick?.teluguName ?? "—"}</strong>
                </div>
                <div className="decision-pair__card decision-pair__card--soft">
                  <span className="micro-label">Loan burden</span>
                  <strong>{money(scenario.profile.loanBurden)}</strong>
                </div>
              </div>
            </div>

            <div className="decision-story">
              <div className="decision-story__card decision-story__card--primary">
                <span className="micro-label">Why this survives</span>
                <strong>{scenario.topPick?.name ?? "No safe crop"}</strong>
                <p>
                  The top lane survives soil fit, water reality, district pressure,
                  and floor-price safety in the same pass.
                </p>
              </div>
              <div className="decision-story__card decision-story__card--secondary">
                <span className="micro-label">What stays visible</span>
                <strong>{scenario.secondPick?.name ?? "No second lane"}</strong>
                <p>
                  The second lane stays on the table as an alternate, not as a
                  false tie with the strongest answer.
                </p>
              </div>
            </div>

            <div className="profile-ledger">
              <div>
                <span className="micro-label">Mandal</span>
                <strong>{scenario.profile.mandal}</strong>
              </div>
              <div>
                <span className="micro-label">Soil</span>
                <strong>{scenario.profile.soilZone}</strong>
              </div>
              <div>
                <span className="micro-label">Water</span>
                <strong>{scenario.profile.waterSource}</strong>
              </div>
              <div>
                <span className="micro-label">Crop history</span>
                <strong>{scenario.profile.lastCrops.join(", ")}</strong>
              </div>
            </div>

            <div className="rejection-rack">
              {scenario.rejected.slice(0, 6).map((item) => (
                <div className="rejection-chip" key={`${item.crop}-${item.reason}`}>
                  <strong>{item.crop}</strong>
                  <span>{item.reason}</span>
                </div>
              ))}
            </div>
          </article>

          <article className="panel trace-panel">
            <div className="trace-panel__header">
              <span className="micro-label">Filter trail</span>
              <h3>How the shortlist shrank</h3>
            </div>

            <div className="trace-timeline">
              {scenario.filterTrace.map((step, index) => (
                <article className="trace-step" key={step.id}>
                  <div className="trace-step__rail">
                    <span>{index + 1}</span>
                  </div>
                  <div className="trace-step__body">
                    <div className="trace-step__top">
                      <strong>{step.title}</strong>
                      <span>
                        kept {step.kept} • removed {step.removed}
                      </span>
                    </div>
                    <p>{step.note}</p>
                    <div className="mini-chip-row">
                      {step.highlights.map((item) => (
                        <span className="mini-chip" key={item}>
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </article>

          <article className="panel telugu-panel">
            <span className="micro-label">Reply that goes back to the farmer</span>
            <h3>Final Telugu response</h3>
            <pre>{scenario.teluguReply}</pre>
          </article>
        </div>
      </div>
    </section>
  );
}
