"use strict";
const $ = id => document.getElementById(id);
let lastRun = null;
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function render(result) {
  lastRun = result;
  const ok = result.status === "completed";
  $("status").textContent = result.status.replaceAll("-", " ");
  $("status").className = `chip ${ok ? "completed" : "attention"}`;
  $("outcome").className = `outcome ${ok ? "" : "attention"}`;
  $("outcome").replaceChildren(node("div", "SERVICE OUTCOME", "section-label"), node("p", result.reason));
  const handoffs = result.audit.filter(record => record.kind === "task");
  $("handoffs").textContent = handoffs.length;
  $("service").textContent = result.service_active ? "Active" : result.status === "rolled-back" ? "Reverted" : "Unchanged";
  $("audit-state").textContent = result.audit_valid ? "Verified" : "Invalid";
  $("agents").replaceChildren(...result.agents.map((agent, index) => {
    const used = handoffs.some(record => record.agent === agent.agent_id);
    const card = node("div", undefined, `agent-card ${used ? "" : "inactive"}`);
    const info = node("div", undefined, "agent-info");
    info.append(node("strong", agent.name), node("small", `${agent.provider} · trust ${agent.trust_score.toFixed(2)} · ${used ? "Dispatched" : "Not dispatched"}`));
    card.append(node("span", String(index + 1).padStart(2,"0"), "agent-number"), info, node("span", agent.domain, "agent-domain"));
    return card;
  }));
  $("trace").replaceChildren(...result.audit.map(record => {
    const row = node("details", undefined, "trace-row");
    const summary = node("summary");
    summary.append(node("span", String(record.sequence).padStart(2,"0"), "trace-num"), node("span", record.kind, "trace-kind"), node("span", record.summary), node("span", record.agent, "trace-agent"));
    row.append(summary, node("pre", JSON.stringify(record, null, 2)));
    return row;
  }));
  $("download").disabled = false;
}
$("run").addEventListener("click", async () => {
  $("run").disabled = true;
  $("status").textContent = "Running";
  try {
    const response = await fetch("/api/run", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({scenario:$("scenario").value})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Run failed");
    render(result);
  } catch (error) {
    $("status").textContent = "Request failed";
    $("outcome").replaceChildren(node("p", error.message));
    $("download").disabled = true;
    lastRun = null;
  } finally { $("run").disabled = false; }
});
$("download").addEventListener("click", () => {
  if (!lastRun) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(lastRun,null,2)+"\n"], {type:"application/json"}));
  const link = node("a");
  link.href = url; link.download = `almadar-${lastRun.scenario}.json`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
fetch("/api/scenarios").then(response => {
  if (!response.ok) throw new Error("Could not load scenarios");
  return response.json();
}).then(data => {
  $("scenario").replaceChildren(...Object.entries(data.scenarios).map(([value,label]) => {
    const option = node("option",label); option.value=value; return option;
  }));
  $("run").disabled = false;
}).catch(error => { $("status").textContent = "Unavailable"; $("outcome").replaceChildren(node("p",error.message)); });
