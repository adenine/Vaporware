const el = (id) => document.getElementById(id);

let pollTimer = null;

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || res.statusText);
  }
  return res.status === 204 ? null : res.json();
}

function renderLogEntries(log) {
  const logBody = document.querySelector("#log-table tbody");
  logBody.innerHTML = "";
  for (const entry of log) {
    const tr = document.createElement("tr");
    const time = new Date(entry.timestamp).toLocaleTimeString();
    tr.innerHTML = `<td>${time}</td><td>${entry.event}</td><td>${JSON.stringify(entry.details)}</td>`;
    logBody.appendChild(tr);
  }
}

function renderSession(session) {
  const statusEl = el("session-status");
  const startBtn = el("start-btn");
  const stopBtn = el("stop-btn");
  const includeCheckbox = el("include-sound-observer");
  const speakText = el("speak-text");
  const speakBtn = el("speak-btn");
  const servicesList = el("services-list");
  const logContext = el("log-context");
  const listenStatus = el("listen-status");

  if (!session) {
    statusEl.textContent = "Idle — no active session";
    statusEl.className = "status idle";
    startBtn.disabled = false;
    stopBtn.disabled = true;
    includeCheckbox.disabled = false;
    speakText.disabled = true;
    speakBtn.disabled = true;
    servicesList.innerHTML = '<li class="muted">No active session</li>';
    logContext.textContent = "";
    listenStatus.textContent = "Not included in this session";
    listenStatus.className = "status idle";
    renderLogEntries([]);
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    return;
  }

  statusEl.textContent = `Active — started ${new Date(session.started_at).toLocaleTimeString()}`;
  statusEl.className = "status active";
  startBtn.disabled = true;
  stopBtn.disabled = false;
  includeCheckbox.disabled = true;

  const tts = session.services.tts;
  const soundObserver = session.services.sound_observer;
  const profileSelect = el("speak-profile");
  servicesList.innerHTML = "";
  if (tts) {
    const li = document.createElement("li");
    li.className = tts.connected ? "connected" : "disconnected";
    li.textContent = `TTS — ${tts.name} (${tts.connected ? "connected" : "disconnected"})` +
      (tts.profiles && tts.profiles.length ? `, profiles: ${tts.profiles.join(", ")}` : "");
    servicesList.appendChild(li);

    const hasProfiles = tts.connected && tts.profiles && tts.profiles.length;
    if (hasProfiles && profileSelect.dataset.loaded !== tts.profiles.join(",")) {
      profileSelect.innerHTML = tts.profiles.map((p) => `<option value="${p}">${p}</option>`).join("");
      profileSelect.dataset.loaded = tts.profiles.join(",");
    }
    profileSelect.disabled = !hasProfiles;
    speakText.disabled = !hasProfiles;
    speakBtn.disabled = !hasProfiles;
  }

  if (soundObserver && soundObserver.included) {
    const li = document.createElement("li");
    li.className = soundObserver.connected ? "connected" : "disconnected";
    li.textContent = `SoundObserver — ${soundObserver.name} (${soundObserver.connected ? "connected" : "disconnected"})`;
    servicesList.appendChild(li);

    if (soundObserver.connected) {
      listenStatus.textContent = "Subscribed — waiting for events from the SoundObserver app";
      listenStatus.className = "status active";
    } else {
      listenStatus.textContent = `Disconnected: ${soundObserver.detail}`;
      listenStatus.className = "status idle";
    }
  } else {
    servicesList.insertAdjacentHTML("beforeend", '<li class="muted">SoundObserver not included this session</li>');
    listenStatus.textContent = "Not included in this session";
    listenStatus.className = "status idle";
  }

  logContext.textContent = "Viewing: live session";
  renderLogEntries(session.log);

  if (!pollTimer) {
    pollTimer = setInterval(refreshCurrent, 2000);
  }
}

function renderHistory(history) {
  const list = el("history-list");
  list.innerHTML = "";
  if (!history.length) {
    list.innerHTML = '<li class="muted">None yet</li>';
    return;
  }
  for (const s of history) {
    const li = document.createElement("li");
    const started = new Date(s.started_at).toLocaleString();
    const status = s.stopped_at ? "closed" : "active";
    li.textContent = `${started} — ${status} — ${s.log.length} log entries (${s.session_id.slice(0, 8)})`;
    li.classList.add("clickable");
    li.addEventListener("click", () => viewHistoricalLog(s.session_id, started));
    list.appendChild(li);
  }
}

async function viewHistoricalLog(sessionId, startedLabel) {
  const session = await api(`/api/sessions/${sessionId}`);
  el("log-context").textContent = `Viewing: closed session from ${startedLabel} (${sessionId.slice(0, 8)})`;
  renderLogEntries(session.log);
}

async function refreshCurrent() {
  const session = await api("/api/sessions/current");
  renderSession(session);
}

async function refreshHistory() {
  const history = await api("/api/sessions");
  renderHistory(history);
}

el("start-btn").addEventListener("click", async () => {
  const observers = el("include-sound-observer").checked ? ["sound_observer"] : [];
  try {
    const session = await api("/api/sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ observers }),
    });
    renderSession(session);
  } catch (e) { alert(e.message); }
});

el("stop-btn").addEventListener("click", async () => {
  try {
    await api("/api/sessions/stop", { method: "POST" });
    renderSession(null);
    await refreshHistory();
  } catch (e) { alert(e.message); }
});

el("speak-btn").addEventListener("click", async () => {
  const text = el("speak-text").value.trim();
  const profile = el("speak-profile").value || null;
  if (!text) return;
  try {
    const result = await api("/api/sessions/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, profile }),
    });
    renderSession(result.session);
    el("speak-text").value = "";
  } catch (e) { alert(e.message); }
});

refreshCurrent();
refreshHistory();
