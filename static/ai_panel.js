"use strict";
// v0.4.0 — persistent right-side offline AI assistant (DEMO, not medically validated).
(() => {
  const el = id => document.getElementById(id);
  const safe = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const TOPIC_NAMES = {muhit: "Kabina muhiti", ovqat: "Ovqat / suv", sensor: "Sensor xatosi", parvoz: "Parvoz / faoliyat"};
  const STATE_NAMES = {mos: "Ehtimoliy sabab", qarshi: "Rad etilgan", noma_lum: "Ma’lumot yo‘q"};
  const STATE_CLASS = {mos: "attention", qarshi: "", noma_lum: "unknown"};
  const ACTION_TEXT = {
    CHECK_CABIN: ["Kabina havosini tekshirish", "Muhit (havo, CO₂, ventilyatsiya) sabab bo‘lishi mumkin."],
    CHECK_INTAKE: ["Ovqat / suvni tekshirish", "Umumiy ovqat yoki suv manbai sabab bo‘lishi mumkin."],
    VERIFY_SENSOR: ["Sensorni qayta o‘lchash", "Ko‘rsatkich qurilma xatosi bo‘lishi mumkin."],
    CHECK_FLIGHT: ["Parvoz / faoliyat bilan bog‘liqlikni ko‘rish", "Holat, yuklama yoki parvoz bosqichi sabab bo‘lishi mumkin."],
    ASK_CONTEXT: ["Qo‘shimcha ma’lumot kerak", "Hech bir sabab yetarli dalil bilan tasdiqlanmadi."],
    REVIEW_CONFLICT: ["Mutaxassis ko‘rib chiqsin", "Bir nechta sabab bir vaqtda mos keldi."],
    REVIEW_MODEL_OUTPUT: ["Qo‘lda tekshiring", "Ba’zi qaydlarda model ishonchi past."],
  };
  const SPECIFIC = new Set(["CHECK_CABIN", "CHECK_INTAKE", "VERIFY_SENSOR", "CHECK_FLIGHT"]);
  let polling = null, status = null;

  async function call(url, method = "GET", payload) {
    const options = {method, headers: {"Content-Type": "application/json"}};
    if (payload !== undefined) options.body = JSON.stringify(payload);
    const res = await fetch(url, options);
    let data = null;
    try { data = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error((data && data.detail && (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail))) || `HTTP ${res.status}`);
    return data;
  }

  function setOpen(open, focus = false) {
    document.body.classList.toggle("ai-open", open);
    el("aiReopen").hidden = open;
    try { localStorage.setItem("astromed.aiOpen", open ? "1" : "0"); } catch (_) {}
    if (open && focus) el("aiRecords").focus({preventScroll: true});
  }

  function renderStatus(s) {
    status = s;
    const pill = el("aiStatusPill"), side = el("aiSidebarStatus");
    let text, cls;
    if (!s.available) { text = "Model o‘rnatilmagan"; cls = "unknown"; }
    else if (s.error) { text = "Xato: model yuklanmadi"; cls = "critical"; }
    else if (s.loading) { text = "Model yuklanmoqda…"; cls = "attention"; }
    else if (s.loaded) { text = `Tayyor · chegara ${s.threshold}`; cls = ""; }
    else { text = "O‘rnatilgan · hali yuklanmagan"; cls = "attention"; }
    pill.textContent = text;
    pill.className = "mini-pill " + cls;
    if (side) side.textContent = !s.available ? "O‘RNATILMAGAN" : s.loaded ? "TAYYOR (DEMO)" : "O‘RNATILGAN (DEMO)";
    el("aiLoadButton").hidden = !(s.available && !s.loaded && !s.loading);
    el("aiRun").disabled = !s.available;
    if (!s.available && !el("aiResult").dataset.filled) {
      const missing = Object.entries(s.files || {}).filter(([, ok]) => !ok).map(([k]) => k).join(", ");
      el("aiResult").innerHTML = `<div class="empty">AI modeli bu kompyuterga hali o‘rnatilmagan (${safe(missing)}).<br>O‘rnatish: <code>run_windows.bat --setup-ai</code><br>Batafsil: README → “AI yordamchi”.</div>`;
    }
    if (s.error) el("aiResult").innerHTML = `<div class="empty">${safe(s.error)}</div>`;
  }

  async function refreshStatus() {
    try { renderStatus(await call("/api/ai/status")); } catch (_) { el("aiStatusPill").textContent = "Server bilan aloqa yo‘q"; }
  }

  function parseRecords(text) {
    const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    if (!lines.length) throw new Error("Kamida bitta qayd kiriting.");
    if (lines.length > 12) throw new Error("Ko‘pi bilan 12 ta qayd.");
    const records = {};
    lines.forEach((line, i) => {
      const m = line.match(/^([A-Za-z0-9_-]{1,12})\s*[:)]\s*(.+)$/);  // "E3: matn" format ham qabul qilinadi
      records[m ? m[1] : `Q${i + 1}`] = m ? m[2] : line;
    });
    return records;
  }

  function renderResult(r) {
    const [title, note] = ACTION_TEXT[r.harakat] || [r.harakat, ""];
    const actCls = SPECIFIC.has(r.harakat) ? "" : r.harakat === "ASK_CONTEXT" ? "ask" : "review";
    const topics = Object.entries(r.ehtimollar).map(([topic, item]) => {
      const ref = (item.dalil || [])[0];
      const rec = ref && r.qaydlar[ref];
      const conf = item.ishonch != null ? ` · ${Math.round(item.ishonch * 100)}%` : "";
      return `<div class="ai-topic"><span class="t">${safe(TOPIC_NAMES[topic] || topic)}</span>
        <span class="mini-pill ${STATE_CLASS[item.holat] || ""}">${safe(STATE_NAMES[item.holat] || item.holat)}${conf}</span>
        ${rec ? `<span class="why">Dalil ${safe(ref)}: ${safe(rec.matn)}</span>` : ""}</div>`;
    }).join("");
    const low = r.past_ishonch && r.past_ishonch.length
      ? `<div class="ai-action review"><small>Past ishonch</small><b>${safe(r.past_ishonch.join(", "))}</b><small>Bu qaydlar bo‘yicha xulosa chiqarilmadi.</small></div>` : "";
    const records = Object.entries(r.qaydlar).map(([ref, q]) =>
      `<li><b>${safe(ref)}</b> → ${safe(q.sinf)} (${Math.round(q.ishonch * 100)}%)<br>${safe(q.matn)}<br><em>EN: ${safe(q.tarjima)}</em></li>`).join("");
    el("aiResult").dataset.filled = "1";
    el("aiResult").innerHTML = `
      <div class="ai-action ${actCls}"><small>Tavsiya etilgan ko‘rib chiqish</small><b>${safe(title)}</b><small>${safe(note)}</small></div>
      ${low}${topics}
      <details class="ai-records"><summary>Har bir qayd tafsiloti · ${safe(r.sekund)} s</summary><ul>${records}</ul></details>
      <p class="ai-warning">${safe(r.ogohlantirish)}</p>`;
  }

  function showProgress(job) {
    el("aiProgress").hidden = false;
    el("aiBar").style.width = `${Math.round((job.progress || 0) * 100)}%`;
    const secs = Math.round((Date.now() - showProgress.started) / 1000);
    el("aiStage").textContent = `${job.stage || "…"} · ${secs} s`;
  }

  async function run() {
    let records;
    try { records = parseRecords(el("aiRecords").value); } catch (err) { el("aiResult").innerHTML = `<div class="empty">${safe(err.message)}</div>`; return; }
    el("aiRun").disabled = true;
    showProgress.started = Date.now();
    try {
      const job = await call("/api/ai/analyze", "POST", {records});
      showProgress(job);
      clearInterval(polling);
      polling = setInterval(async () => {
        try {
          const j = await call(`/api/ai/jobs/${encodeURIComponent(job.job_id)}`);
          showProgress(j);
          if (j.status === "done" || j.status === "error") {
            clearInterval(polling);
            el("aiProgress").hidden = true;
            el("aiRun").disabled = false;
            if (j.status === "done") renderResult(j.result);
            else el("aiResult").innerHTML = `<div class="empty">Tahlil bajarilmadi: ${safe(j.error)}</div>`;
            refreshStatus();
          }
        } catch (err) {
          clearInterval(polling); el("aiProgress").hidden = true; el("aiRun").disabled = false;
          el("aiResult").innerHTML = `<div class="empty">${safe(err.message)}</div>`;
        }
      }, 1500);
    } catch (err) {
      el("aiRun").disabled = false;
      el("aiResult").innerHTML = `<div class="empty">${safe(err.message)}</div>`;
    }
  }

  el("aiCollapse").addEventListener("click", () => setOpen(false));
  el("aiReopen").addEventListener("click", () => setOpen(true, true));
  el("aiRun").addEventListener("click", run);
  el("aiClear").addEventListener("click", () => { el("aiRecords").value = ""; el("aiRecords").focus(); });
  el("aiDemo").addEventListener("click", async () => {
    try {
      const {records} = await call("/api/ai/demo");
      el("aiRecords").value = Object.entries(records).map(([k, v]) => `${k}: ${v}`).join("\n");
    } catch (err) { el("aiResult").innerHTML = `<div class="empty">${safe(err.message)}</div>`; }
  });
  el("aiLoadButton").addEventListener("click", async () => {
    try { renderStatus(await call("/api/ai/load", "POST")); } catch (err) { el("aiResult").innerHTML = `<div class="empty">${safe(err.message)}</div>`; }
    const t = setInterval(async () => { await refreshStatus(); if (status && !status.loading) clearInterval(t); }, 3000);
  });
  let startOpen = true;
  try { startOpen = localStorage.getItem("astromed.aiOpen") !== "0"; } catch (_) {}
  setOpen(startOpen && window.innerWidth > 790);
  refreshStatus();
})();
