"use strict";
const $ = (id) => document.getElementById(id);
let result,
  tab = "trace";
const titles = {
  Task_RCA: "Root cause & topology",
  Task_CEAndImpact: "Subscriber impact",
  Task_Prioritize: "Prioritise & route",
  Task_HandleAndRemediate: "Recommend remediation",
  Task_CrossDomainRemediation: "Coordinate domains",
  Task_ConfirmRestoration: "Verify service restoration",
};
function element(tag, text, cls) {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
}
function json(value) {
  return element("pre", JSON.stringify(value, null, 2));
}
function process() {
  const host = $("process");
  host.replaceChildren();
  for (const [id, title] of Object.entries(titles)) {
    const done = result?.results[id];
    const n = element(
      "div",
      undefined,
      "step " +
        (done ? "done" : "wait") +
        (id !== "Task_RCA" && id !== "Task_CEAndImpact" ? " wide" : ""),
    );
    n.append(
      element("b", title),
      element(
        "small",
        id === "Task_RCA" || id === "Task_CEAndImpact"
          ? "Digital Twin · parallel branch"
          : id === "Task_Prioritize"
            ? "Digital Twin · evidence join"
            : id === "Task_HandleAndRemediate"
              ? "Complaint Management"
              : "Network Operations",
      ),
    );
    host.append(n);
  }
}
function topology() {
  const i = result?.incident || {
    cell_ids: ["ALM-CELL-01", "ALM-CELL-02", "ALM-CELL-03"],
    transport_id: "ALM-BH-01",
  };
  const cells = element("div", undefined, "cells");
  for (const id of i.cell_ids) cells.append(element("div", id, "node"));
  const restored = result?.status === "restored";
  const bh = element(
    "div",
    undefined,
    "node " + (restored ? "healthy" : "fault"),
  );
  bh.append(
    element("b", i.transport_id),
    element("small", restored ? "Backup path active" : "Optical degradation"),
  );
  const core = element("div", undefined, "node");
  core.append(
    element("b", "Mobile core"),
    element("small", "No primary fault"),
  );
  $("topology").replaceChildren(
    cells,
    element("div", "→", "arrow"),
    bh,
    element("div", "→", "arrow"),
    core,
  );
}
function inspect() {
  const host = $("inspector");
  host.replaceChildren();
  if (!result) {
    host.append(
      element("p", "Run a condition to inspect the fabric.", "muted"),
    );
    return;
  }
  if (tab === "trace") {
    for (const r of result.audit) {
      const d = element("details");
      const s = element("summary");
      s.append(
        element("span", r.kind.toUpperCase()),
        document.createTextNode(r.agent + " · " + r.summary),
      );
      d.append(s, json(r));
      host.append(d);
    }
  }
  if (tab === "prompts") {
    host.append(
      element(
        "p",
        "Local Task-T envelope and HMAC attestation profile. This is not an interoperable A2A-T SDK client.",
        "muted",
      ),
    );
    for (const m of result.messages) {
      const e = m.params.message.metadata.local_a2at_profile;
      const d = element("details");
      d.append(
        element(
          "summary",
          e.payload.initiator +
            " → " +
            e.payload.executor +
            " · " +
            e.payload.activity,
        ),
        json(m),
      );
      host.append(d);
    }
  }
  if (tab === "explain") {
    for (const [id, r] of Object.entries(result.results)) {
      if (!r.explain) continue;
      const d = element("div", undefined, "explanation");
      d.append(
        element("b", titles[id] || id),
        element("p", r.explain.summary),
        element("small", "Evidence: " + r.explain.evidence_refs.join(" · ")),
        json(r),
      );
      host.append(d);
    }
  }
  if (tab === "governance") {
    host.append(
      element(
        "p",
        "Trust scores are advisory observations. Payload, scope and signature validation independently control dispatch.",
        "muted",
      ),
    );
    const table = element("table");
    const head = element("tr");
    for (const title of ["Agent", "Verdict", "Score", "Reason"])
      head.append(element("th", title));
    table.append(head);
    for (const e of result.governance.events) {
      const row = element("tr");
      for (const v of [e.agent, e.verdict, e.score.toFixed(2), e.reason])
        row.append(element("td", v));
      table.append(row);
    }
    host.append(table);
  }
  if (tab === "design")
    host.append(
      element(
        "p",
        "Six operator activities compiled into a process graph, lane playbooks and version-pinned templates.",
        "muted",
      ),
      json(result.design),
    );
}
function render() {
  const i = result.incident;
  $("incident").textContent = i.incident_id;
  $("area").textContent = i.area;
  $("subscribers").textContent = i.affected_subscribers.toLocaleString();
  const post = result.results.Task_ConfirmRestoration;
  $("throughput").replaceChildren(
    document.createTextNode(
      String(post?.throughput_mbps ?? i.throughput_mbps) + " ",
    ),
    element("em", "Mbps"),
  );
  $("loss").replaceChildren(
    document.createTextNode(
      String(post?.packet_loss_pct ?? i.packet_loss_pct) + " ",
    ),
    element("em", "%"),
  );
  $("throughput-note").textContent = post
    ? i.throughput_mbps +
      " → " +
      post.throughput_mbps +
      " Mbps · target ≥ " +
      i.min_throughput_mbps
    : "Closure threshold ≥ " + i.min_throughput_mbps + " Mbps";
  $("loss-note").textContent = post
    ? i.packet_loss_pct +
      " → " +
      post.packet_loss_pct +
      "% · target ≤ " +
      i.max_packet_loss_pct +
      "%"
    : "Closure threshold ≤ " + i.max_packet_loss_pct + "%";
  $("status").textContent = result.status.replaceAll("-", " ").toUpperCase();
  $("reason").textContent = result.reason;
  $("audit-state").textContent =
    result.audit.length +
    " records · " +
    (result.audit_valid ? "Hash chain verified" : "Audit invalid");
  $("actions").replaceChildren(element("p", "Domain actions"));
  for (const a of result.domain_actions)
    $("actions").append(element("p", a.domain + " · " + a.action));
  if (!result.domain_actions.length)
    $("actions").append(element("p", "No network changes executed.", "muted"));
  $("export").disabled = false;
  process();
  topology();
  inspect();
}
$("run").addEventListener("click", async () => {
  $("run").disabled = true;
  $("run").textContent = "Running assurance…";
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: $("scenario").value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    result = data;
    render();
  } catch (e) {
    $("reason").textContent = e.message;
    $("status").textContent = "RUN FAILED";
  } finally {
    $("run").disabled = false;
    $("run").textContent = "Run assurance";
  }
});
for (const b of document.querySelectorAll("[data-tab]"))
  b.addEventListener("click", () => {
    tab = b.dataset.tab;
    for (const x of document.querySelectorAll("[data-tab]"))
      x.classList.toggle("active", x === b);
    inspect();
  });
$("export").addEventListener("click", () => {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }),
  );
  const link = element("a");
  link.href = url;
  link.download = "almadar-" + result.scenario + ".json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
fetch("/api/scenarios")
  .then((r) => r.json())
  .then((data) => {
    for (const [id, label] of Object.entries(data.scenarios)) {
      const option = element("option", label);
      option.value = id;
      $("scenario").append(option);
    }
  })
  .catch((e) => {
    $("reason").textContent = e.message;
    $("run").disabled = true;
  });
process();
topology();
