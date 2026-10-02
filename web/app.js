// Kaagaz web app: three big actions, a confirmation card, what's next, and the inbox.
const API = (window.KAAGAZ_API || "").replace(/\/$/, "");
const $ = (s) => document.querySelector(s);

const BANNER = {
  demo: "SAMPLE DATA ONLY — uploads are processed by hosted AI services (Google, ElevenLabs). Do not upload real personal documents.",
  real: "LOCAL AI MODE — photos and voice recordings are processed on this device. Only the confirmed reminder details are synced to the database.",
};
const LABEL = { d30: "30 दिन पहले वाला", d7: "7 दिन पहले वाला", d1: "1 दिन पहले वाला", now: "अभी", snooze: "आपकी बताई तारीख़ वाला", escalation: "बेटे को सूचना" };
const CHANGES = ["create_obligation", "mark_done", "snooze", "update_obligation"];
const GONE = "यह काग़ज़ या आवाज़ अब सर्वर पर नहीं है — कृपया फिर से भेजिए।";
const NETWORK = "सर्वर से जुड़ नहीं पाए — इंटरनेट देखिए।";

const saved = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};
const params = new URLSearchParams(location.search);
const state = {
  token: saved.get("kaagaz.token"),
  role: ["parent", "son"].includes(params.get("role")) ? params.get("role") : saved.get("kaagaz.role") || "parent",
  health: null, data: null, card: null, inputId: null, recorder: null, seen: new Set(), primed: false,
};

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const inr = (n) => (n == null ? "" : "₹" + Math.round(n).toLocaleString("en-IN"));
const hiDate = (iso) => (iso ? new Date(iso + "T00:00:00").toLocaleDateString("hi-IN", { day: "numeric", month: "long", year: "numeric" }) : "");
const hiWhen = (iso) => new Date(iso).toLocaleString("hi-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function toast(text) {
  const el = $("#toast");
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.hidden = true; }, 5000);
}

function status(html) {
  const el = $("#status");
  el.innerHTML = html || "";
  el.hidden = !html;
}

async function api(path, opts = {}, retried = false) {
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  let body = opts.body;
  if (opts.json !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(opts.json); }
  let r;
  try { r = await fetch(API + path, { method: opts.method || "GET", headers, body }); }
  catch { throw new Error(NETWORK); }
  if (r.status === 401 && !retried && path !== "/api/households") {
    state.token = null;
    await ensureHousehold();
    return api(path, opts, true);
  }
  if (!r.ok) {
    let d = {};
    try { d = await r.json(); } catch { /* not json */ }
    const e = new Error(typeof d.detail === "string" ? d.detail : `HTTP ${r.status}`);
    e.status = r.status;
    throw e;
  }
  return (r.headers.get("content-type") || "").includes("json") ? r.json() : r.blob();
}

async function wake() {
  const t0 = Date.now();
  for (;;) {
    try {
      const r = await fetch(API + "/api/health");
      if (r.ok) { state.health = await r.json(); break; }
    } catch { /* still asleep */ }
    if (Date.now() - t0 > 120000) {
      $("#waking").innerHTML = "<div>सर्वर नहीं जागा — थोड़ी देर बाद पेज फिर खोलिए। <small>Server didn't wake; try again shortly.</small></div>";
      return false;
    }
    await sleep(3000);
  }
  $("#waking").hidden = true;
  document.body.classList.remove("asleep");
  const b = $("#banner");
  b.textContent = BANNER[state.health.mode] || "";
  b.className = `banner ${state.health.mode}`;
  b.hidden = false;
  return true;
}

async function ensureHousehold() {
  if (state.token) return;
  const r = await api("/api/households", { method: "POST" });
  state.token = r.token;
  saved.set("kaagaz.token", r.token);
}

function setRole(role) {
  state.role = role;
  saved.set("kaagaz.role", role);
  document.querySelectorAll(".role").forEach((b) => b.classList.toggle("on", b.dataset.role === role));
  document.body.dataset.role = role;
  state.primed = false;
  if (state.health) refresh();
}

async function refresh() {
  if (!state.token) return;
  try {
    state.data = await api(`/api/state?role=${state.role}`);
  } catch (e) { console.warn(e); return; }
  renderItems();
  renderInbox();
  const fresh = state.data.inbox.filter((n) => !n.read && !state.seen.has(n.id));
  state.data.inbox.forEach((n) => state.seen.add(n.id));
  if (state.primed && fresh.length) {
    toast(`${fresh[0].kind === "escalation" ? "⚠️" : "🔔"} ${fresh[0].text_hi}`);
    navigator.vibrate?.(200);
  }
  state.primed = true;
}

function renderItems() {
  const { obligations, mode } = state.data;
  const ul = $("#items");
  if (!obligations.length) {
    ul.innerHTML = `<li class="empty">अभी कुछ नहीं। ऊपर से काग़ज़ दिखाइए या बोलिए। <small>Nothing yet.</small></li>`;
    return;
  }
  ul.innerHTML = obligations.map((o) => {
    const next = o.next
      ? `<div class="next">अगला: ${esc(LABEL[o.next.label] || o.next.label)} — ${esc(hiWhen(o.next.at))}${mode === "real" && o.next.kind === "reminder" ? " <small>(सुबह 9 से 9:30 के बीच)</small>" : ""}</div>`
      : "";
    const btns = o.status === "active"
      ? `<div class="btns"><button type="button" class="primary" data-done="${o.id}">हो गया</button><button type="button" class="secondary" data-snooze="${o.id}">बाद में याद दिलाना</button></div>`
      : "";
    return `<li class="item ${esc(o.status)}">
      <div class="row"><strong>${esc(o.title_hi || o.title)}</strong><span class="amt">${inr(o.amount_inr)}</span></div>
      <div class="meta">आख़िरी तारीख़ ${esc(hiDate(o.due_date))}${o.status === "done" ? " · ✅ हो गया" : ""}</div>
      ${next}${btns}</li>`;
  }).join("");
}

function renderInbox() {
  const { inbox, unread } = state.data;
  $("#unread").hidden = !unread;
  $("#unread").textContent = unread;
  $("#inbox").innerHTML = inbox.length
    ? inbox.map((n) => `<li class="note ${esc(n.kind)} ${n.read ? "read" : ""}">
        <div>${n.kind === "escalation" ? "⚠️" : "🔔"} ${esc(n.text_hi)}</div>
        <div class="en">${esc(n.text_en)}</div>
        <div class="btns"><button type="button" class="secondary" data-play="${esc(n.id)}">▶ सुनिए</button>${n.read ? "" : `<button type="button" class="secondary" data-read="${esc(n.id)}">पढ़ लिया</button>`}</div>
      </li>`).join("")
    : `<li class="empty">${state.role === "son" ? "अभी कोई चेतावनी नहीं। <small>No alerts.</small>" : "अभी कोई reminder नहीं। <small>No reminders yet.</small>"}</li>`;
}

let audio;
async function speak(text) {
  if (!text) return;
  if (state.health?.tts === "elevenlabs") {
    try {
      const blob = await api("/api/tts", { method: "POST", json: { text } });
      audio?.pause();
      audio = new Audio(URL.createObjectURL(blob));
      await audio.play();
      return;
    } catch (e) { console.warn("server voice failed, using browser voice", e); }
  }
  if ("speechSynthesis" in window) {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "hi-IN";
    const v = speechSynthesis.getVoices().find((x) => x.lang?.toLowerCase().startsWith("hi"));
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  }
}

async function sendInput(form, label) {
  hideCard();
  status(`<div class="spin"></div><div>${label}</div>`);
  form.append("role", state.role);
  try {
    const { input_id: id } = await api("/api/inputs", { method: "POST", body: form });
    state.inputId = id;
    const t0 = Date.now();
    for (;;) {
      await sleep(2000);
      let p;
      try { p = await api(`/api/inputs/${id}`); }
      catch (e) { throw e.status === 404 ? new Error(GONE) : e; }
      if (p.status === "ready") { status(""); showCard(p.card); return; }
      if (p.status === "failed") throw new Error(p.message || "कुछ गड़बड़ हुई — फिर से कोशिश करें।");
      if (Date.now() - t0 > 300000) throw new Error("बहुत देर लग रही है — फिर से कोशिश करें।");
    }
  } catch (e) {
    status(`<div class="err">${esc(e.message)}</div>`);
  }
}

async function shrink(blob) {
  const bmp = await createImageBitmap(blob).catch(() => null);
  if (!bmp) return blob;   // can't decode here (e.g. HEIC on desktop): send as is; the server caps size
  const scale = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * scale);
  c.height = Math.round(bmp.height * scale);
  c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
  return new Promise((r) => c.toBlob(r, "image/jpeg", 0.85));
}

async function sendPhoto(blob) {
  const f = new FormData();
  f.append("kind", "photo");
  f.append("file", await shrink(blob), "paper.jpg");
  await sendInput(f, "काग़ज़ पढ़ रहा हूँ… <small>Reading your paper</small>");
}

async function toggleRecord() {
  const btn = $("#btn-speak");
  if (state.recorder) { state.recorder.stop(); return; }
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
  catch { toast("माइक की अनुमति नहीं मिली। ❓ पूछिए में लिखकर भी बता सकते हैं।"); return; }
  const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((t) => window.MediaRecorder?.isTypeSupported(t)) || "";
  const rec = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
  const chunks = [];
  rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  rec.onstop = async () => {
    stream.getTracks().forEach((t) => t.stop());
    clearTimeout(rec.limit);
    state.recorder = null;
    btn.classList.remove("rec");
    btn.querySelector(".hi").textContent = "बोलिए";
    btn.querySelector(".en").textContent = "Speak";
    const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
    if (blob.size < 1000) { toast("कुछ सुनाई नहीं दिया — फिर से बोलिए।"); return; }
    const f = new FormData();
    f.append("kind", "voice");
    f.append("file", blob, (rec.mimeType || "").includes("mp4") ? "voice.m4a" : "voice.webm");
    await sendInput(f, "सुन रहा हूँ… <small>Listening</small>");
  };
  rec.start();
  state.recorder = rec;
  rec.limit = setTimeout(() => { if (rec.state === "recording") rec.stop(); }, 30000);
  btn.classList.add("rec");
  btn.querySelector(".hi").textContent = "रोकिए";
  btn.querySelector(".en").textContent = "Tap to stop · max 30 s";
}

function field(i, key, label, value, type, flagged, evidence) {
  return `<label class="f ${flagged ? "flag" : ""}"><span>${label}${flagged ? " — <em>काग़ज़ पर देखकर पक्का कीजिए</em>" : ""}</span>
    <input data-i="${i}" data-k="${key}" type="${type}" value="${esc(value ?? "")}" ${type === "number" ? 'inputmode="numeric" min="0" step="1"' : ""}>
    ${evidence ? `<small class="ev">काग़ज़ पर: “${esc(evidence)}”</small>` : ""}</label>`;
}

function actionHtml(a, i) {
  const name = esc(a.title_hi || a.title);
  if (a.tool === "create_obligation") {
    const flag = (k) => (a.needs_check || []).includes(k);
    return `<div class="act create"><h3>${name}</h3>
      ${field(i, "title_hi", "नाम", a.title_hi || a.title, "text", false, "")}
      ${field(i, "amount_inr", "रकम (₹)", a.amount_inr, "number", flag("amount_inr"), a.evidence_amount)}
      ${field(i, "due_date", "आख़िरी तारीख़", a.due_date, "date", flag("due_date"), a.evidence_due_date)}
      ${field(i, "action", "क्या करना है", a.action, "text", false, "")}
      ${a.consequence ? `<p class="cons">न करने पर: ${esc(a.consequence)}${a.evidence_consequence ? `<small class="ev">काग़ज़ पर: “${esc(a.evidence_consequence)}”</small>` : ""}</p>` : ""}
      <label class="check"><input type="checkbox" data-i="${i}" data-k="escalate" ${a.escalate ? "checked" : ""}> अगर मैं भूल जाऊँ तो बेटे को बताना</label>
      <p class="plan">याद दिलाऊँगा: ${a.remind_offsets_days.map((d) => `${d} दिन पहले`).join(", ")}</p></div>`;
  }
  if (a.tool === "mark_done") return `<div class="act">✅ ${name} — हो गया</div>`;
  if (a.tool === "snooze") return `<div class="act">⏰ ${name} — ${esc(hiDate(a.until))} को फिर याद दिलाऊँगा</div>`;
  if (a.tool === "update_obligation") {
    const bits = [a.amount_inr ? `नई रकम ${inr(a.amount_inr)}` : "", a.due_date ? `नई तारीख़ ${esc(hiDate(a.due_date))}` : ""].filter(Boolean).join(", ");
    return `<div class="act">✏️ ${name} — ${bits}</div>`;
  }
  if (a.tool === "answer") return `<div class="act answer">${esc(a.text_hi)}</div>`;
  return `<div class="act clarify">${esc(a.question_hi)}</div>`;
}

function showCard(card) {
  state.card = card;
  const changes = card.actions.some((a) => CHANGES.includes(a.tool));
  const el = $("#card");
  el.innerHTML = `${card.transcript ? `<p class="said">आपने कहा: “${esc(card.transcript)}”</p>` : ""}
    ${card.summary_hi ? `<p class="summary">${esc(card.summary_hi)}</p>` : ""}
    ${card.actions.map(actionHtml).join("")}
    <div class="btns">
      ${changes ? '<button type="button" id="c-ok" class="primary">सही है ✓</button><button type="button" id="c-edit" class="secondary">बदलें</button>' : ""}
      <button type="button" id="c-play" class="secondary">▶ फिर सुनिए</button>
      <button type="button" id="c-no" class="secondary">${changes ? "रद्द" : "ठीक है"}</button>
    </div>`;
  el.hidden = false;
  el.scrollIntoView({ behavior: "smooth", block: "start" });
  speak(card.readback_hi);
}

function hideCard() {
  $("#card").hidden = true;
  state.card = null;
}

function collectActions() {
  const acts = structuredClone(state.card.actions);
  document.querySelectorAll("#card [data-k]").forEach((inp) => {
    const a = acts[Number(inp.dataset.i)];
    const k = inp.dataset.k;
    if (k === "escalate") a.escalate = inp.checked;
    else if (k === "amount_inr") a.amount_inr = inp.value === "" ? null : Number(inp.value);
    else a[k] = inp.value.trim() || null;
  });
  return acts.filter((a) => CHANGES.includes(a.tool));
}

async function confirmCard() {
  const btn = $("#c-ok");
  if (btn) btn.disabled = true;   // one tap, one save (the server also guards against repeats)
  try {
    await api(`/api/inputs/${state.inputId}/confirm`, { method: "POST", json: { actions: collectActions(), role: state.role } });
    hideCard();
    toast("सेव हो गया — मैं याद दिलाऊँगा ✓");
    refresh();
  } catch (e) {
    if (btn) btn.disabled = false;
    toast(e.status === 404 ? GONE : e.message);
  }
}

function b64ToBytes(b64) {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

async function enablePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    toast("इस ब्राउज़र में फ़ोन सूचना नहीं चलती — सब कुछ यहीं inbox में दिखेगा। (iPhone: पहले Home Screen पर जोड़ें)");
    return;
  }
  if (!state.health?.push_key) { toast("फ़ोन सूचना अभी उपलब्ध नहीं — inbox में सब दिखेगा।"); return; }
  if ((await Notification.requestPermission()) !== "granted") { toast("अनुमति नहीं मिली — inbox में सब दिखता रहेगा।"); return; }
  try {
    const reg = await navigator.serviceWorker.ready;
    const sub = (await reg.pushManager.getSubscription())
      || (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(state.health.push_key) }));
    await api("/api/push/subscribe", { method: "POST", json: { role: state.role, subscription: sub.toJSON() } });
    toast(state.role === "son" ? "बेटे के फ़ोन पर सूचना चालू ✓" : "पापा के फ़ोन पर सूचना चालू ✓");
  } catch (e) { toast(e.message || "सूचना चालू नहीं हो पाई।"); }
}

function wire() {
  document.querySelectorAll(".role").forEach((b) => b.addEventListener("click", () => setRole(b.dataset.role)));
  $("#btn-speak").addEventListener("click", toggleRecord);
  $("#btn-scan").addEventListener("click", () => $("#file").click());
  $("#file").addEventListener("change", (e) => { const f = e.target.files[0]; e.target.value = ""; if (f) sendPhoto(f); });
  $("#btn-ask").addEventListener("click", () => { $("#ask-box").hidden = false; $("#ask-text").focus(); });
  $("#ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $("#ask-text").value.trim();
    if (!text) return;
    $("#ask-text").value = "";
    const f = new FormData();
    f.append("kind", "text");
    f.append("text", text);
    sendInput(f, "सोच रहा हूँ… <small>Thinking</small>");
  });
  document.querySelectorAll(".sample").forEach((b) => b.addEventListener("click", async () => {
    const r = await fetch(`samples/${b.dataset.sample}.jpg`);
    sendPhoto(await r.blob());
  }));
  $("#card").addEventListener("click", (e) => {
    const id = e.target.id;
    if (id === "c-ok") confirmCard();
    else if (id === "c-edit") $("#card input")?.focus();
    else if (id === "c-play") speak(state.card?.readback_hi);
    else if (id === "c-no") hideCard();
  });
  $("#items").addEventListener("click", async (e) => {
    const t = e.target;
    try {
      if (t.dataset.done) {
        await api(`/api/obligations/${t.dataset.done}/done`, { method: "POST", json: { role: state.role } });
        toast("बहुत बढ़िया — हो गया ✓");
        refresh();
      } else if (t.dataset.snooze) {
        t.closest(".btns").innerHTML = `<input type="date" class="snooze-date" min="${state.data.today}" aria-label="किस तारीख़ को"><button type="button" class="primary" data-snooze-ok="${t.dataset.snooze}">ठीक है</button>`;
      } else if (t.dataset.snoozeOk) {
        const until = t.parentElement.querySelector(".snooze-date").value;
        if (!until) { toast("तारीख़ चुनिए।"); return; }
        await api(`/api/obligations/${t.dataset.snoozeOk}/snooze`, { method: "POST", json: { until, role: state.role } });
        toast(`${hiDate(until)} को फिर याद दिलाऊँगा ✓`);
        refresh();
      }
    } catch (err) { toast(err.message); }
  });
  $("#inbox").addEventListener("click", async (e) => {
    const t = e.target;
    const note = state.data?.inbox.find((n) => n.id === (t.dataset.play || t.dataset.read));
    if (t.dataset.play && note) speak(note.text_hi);
    if (t.dataset.read || t.dataset.play) {
      try { await api(`/api/notifications/${encodeURIComponent(note.id)}/read`, { method: "POST" }); refresh(); }
      catch (err) { console.warn(err); }
    }
  });
  $("#btn-push").addEventListener("click", enablePush);
}

async function init() {
  wire();
  document.querySelectorAll(".role").forEach((b) => b.classList.toggle("on", b.dataset.role === state.role));
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
  if (!(await wake())) return;
  try { await ensureHousehold(); } catch (e) { toast(e.message); return; }
  await refresh();
  setInterval(() => { if (document.visibilityState === "visible") refresh(); }, 5000);
}

init();
