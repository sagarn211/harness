const snippetInput = document.querySelector("#snippet");
const analyzeButton = document.querySelector("#analyze");
const toast = document.querySelector("#toast");
const state = { requestId: null, proposal: null, markdown: "", toastTimer: null };

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("show"), 4000);
}

function updateEditor() {
  const code = snippetInput.value;
  const lines = code ? code.split(/\r\n?|\n/).length - (code.endsWith("\n") ? 1 : 0) : 0;
  document.querySelector("#line-numbers").textContent = lines
    ? Array.from({ length: lines }, (_, index) => index + 1).join("\n")
    : "1";
  document.querySelector("#line-count").textContent = lines;
  document.querySelector("#character-count").textContent = code.length;
  document.querySelector("#source-state").textContent = code.trim() ? "Ready to analyze" : "Ready for input";
}

function setWorkflowState(label, type = "") {
  const badge = document.querySelector("#workflow-state");
  badge.className = `state-badge ${type}`;
  badge.innerHTML = `<span></span>${label}`;
}

function updateStatuses(statuses) {
  for (const status of document.querySelectorAll("#status-strip [data-status]")) {
    status.classList.toggle("complete", Boolean(statuses?.[status.dataset.status]));
  }
}

function renderEvents(events = []) {
  const list = document.querySelector("#event-list");
  list.replaceChildren();
  document.querySelector("#event-count").textContent = `${events.length} EVENT${events.length === 1 ? "" : "S"}`;
  document.querySelector("#activity-empty").hidden = events.length > 0;
  for (const event of events) {
    const item = document.createElement("li");
    item.className = "event-item";
    const title = document.createElement("strong");
    title.textContent = `${String(event.seq).padStart(2, "0")} · ${event.state}`;
    const time = document.createElement("small");
    time.textContent = new Date(event.at).toLocaleTimeString();
    item.append(title, time);
    list.append(item);
  }
}

function renderEvidence(evidence = []) {
  const summary = document.querySelector("#evidence-summary");
  summary.hidden = evidence.length === 0;
  if (!evidence.length) return;
  const phrases = evidence.flatMap((item) => item.extracted?.matched_phrase || []);
  summary.replaceChildren();
  const label = document.createElement("strong");
  label.textContent = "Untrusted text recorded: ";
  summary.append(label, document.createTextNode(phrases.join(", ") || "untrusted model output"));
}

function renderProposal(response) {
  const proposal = response.proposal;
  state.requestId = response.request_id;
  state.proposal = proposal;
  document.querySelector("#empty-state").hidden = true;
  document.querySelector("#proposal-view").hidden = false;
  document.querySelector("#detected-language").textContent = proposal.language.name;
  document.querySelector("#explanation").value = proposal.explanation;
  document.querySelector("#documentation").value = proposal.documentation;
  document.querySelector("#proposal-hash").textContent = proposal.output_hash;
  document.querySelector("#explanation").disabled = false;
  document.querySelector("#documentation").disabled = false;
  document.querySelector("#review-controls").hidden = false;
  document.querySelector("#final-result").hidden = true;
  setWorkflowState("AWAITING REVIEW", "pending");
  updateStatuses({ detected: true, explained: Boolean(proposal.explanation) });
  renderEvents(response.events);
  renderEvidence(response.untrusted_evidence);
}

async function readResponse(response) {
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status}).`);
  return result;
}

async function analyze() {
  if (!snippetInput.value.trim()) {
    showToast("Enter a code snippet first.");
    snippetInput.focus();
    return;
  }
  analyzeButton.disabled = true;
  analyzeButton.textContent = "Analyzing with Gemini...";
  setWorkflowState("ANALYZING", "pending");
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: snippetInput.value }),
    });
    const result = await readResponse(response);
    renderProposal(result);
  } catch (error) {
    setWorkflowState("ANALYSIS FAILED", "failed");
    showToast(error.message || "Could not reach the local server.");
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.innerHTML = '<span aria-hidden="true">↗</span> Analyze snippet';
  }
}

async function review(decision) {
  const approverId = document.querySelector("#approver-id").value.trim();
  if (!approverId) {
    showToast("Enter a reviewer ID before recording a decision.");
    return;
  }
  const approveButton = document.querySelector("#approve");
  const rejectButton = document.querySelector("#reject");
  approveButton.disabled = true;
  rejectButton.disabled = true;
  setWorkflowState(decision === "approve" ? "FORMATTING" : "REJECTING", "pending");
  const payload = {
    request_id: state.requestId,
    approver_id: approverId,
    decision,
  };
  if (decision === "approve") {
    payload.explanation = document.querySelector("#explanation").value;
    payload.documentation = document.querySelector("#documentation").value;
  }

  try {
    const response = await fetch("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await readResponse(response);
    renderEvents(result.events);
    if (decision === "reject") {
      document.querySelector("#explanation").disabled = true;
      document.querySelector("#documentation").disabled = true;
      document.querySelector("#review-controls").hidden = true;
      updateStatuses({ detected: true, explained: true });
      setWorkflowState("REJECTED", "failed");
      showToast("Proposal rejected; it was not formatted or delivered.");
      return;
    }
    state.markdown = result.result.formatted_markdown;
    document.querySelector("#formatted-markdown").textContent = state.markdown;
    document.querySelector("#chain-status").textContent = result.result.event_chain_verified
      ? "✓ Event chain verified"
      : "! Event chain verification failed";
    document.querySelector("#final-result").hidden = false;
    document.querySelector("#explanation").disabled = true;
    document.querySelector("#documentation").disabled = true;
    document.querySelector("#review-controls").hidden = true;
    updateStatuses(result.result.four_statuses);
    setWorkflowState("DELIVERED", "complete");
    showToast("Approved Markdown is ready to copy or download.");
  } catch (error) {
    setWorkflowState("REVIEW FAILED", "failed");
    showToast(error.message || "Could not record the review.");
  } finally {
    approveButton.disabled = false;
    rejectButton.disabled = false;
  }
}

snippetInput.addEventListener("input", updateEditor);
snippetInput.addEventListener("scroll", () => {
  document.querySelector("#line-numbers").scrollTop = snippetInput.scrollTop;
});
analyzeButton.addEventListener("click", analyze);
document.querySelector("#approve").addEventListener("click", () => review("approve"));
document.querySelector("#reject").addEventListener("click", () => review("reject"));
document.querySelector("#copy-markdown").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(state.markdown);
    showToast("Markdown copied.");
  } catch {
    showToast("Clipboard access is unavailable in this browser.");
  }
});
document.querySelector("#download-markdown").addEventListener("click", () => {
  const file = new Blob([state.markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = "snippet-documentation.md";
  link.click();
  URL.revokeObjectURL(url);
});

async function checkConfiguration() {
  try {
    const response = await fetch("/api/health");
    const health = await response.json();
    const label = document.querySelector("#key-status");
    label.textContent = health.gemini_key_configured ? "API key configured" : "API key missing in server shell";
    label.classList.toggle("key-missing", !health.gemini_key_configured);
  } catch {
    document.querySelector("#key-status").textContent = "Local server unavailable";
  }
}

updateEditor();
checkConfiguration();