const STEP_COLORS = ["#16a34a", "#0891b2", "#d97706", "#7c3aed", "#dc2626"];

import { useState } from "react";

export default function FilterStepper({ steps }) {
  const [active, setActive] = useState(0);
  const step = steps[active];
  return (
    <div className="filter-stepper-wrap">
      <div className="filter-stepper">
        {steps.map((s, i) => (
          <button
            type="button"
            key={s.id}
            className={`filter-step-btn ${i === active ? "filter-step-btn--active" : ""}`}
            onClick={() => setActive(i)}
          >
            <span
              className="filter-step-num"
              style={i === active ? { background: STEP_COLORS[i], color: "#fff", borderColor: "transparent" } : {}}
            >
              {i + 1}
            </span>
            <span className="filter-step-label">{s.title}</span>
          </button>
        ))}
      </div>
      {step && (
        <div className="filter-step-detail" style={{ borderTopColor: STEP_COLORS[active] }}>
          <div className="filter-step-detail__top">
            <strong>{step.title}</strong>
            <span>kept {step.kept} · removed {step.removed}</span>
          </div>
          <p>{step.note}</p>
          <div className="mini-chip-row">
            {step.highlights.map((item) => (
              <span className="mini-chip" key={item}>{item}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
