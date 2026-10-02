// HTML builders. Pure: data in, HTML string out, every value escaped. app.js owns the DOM and the state.
import { getLang, pick, t } from "./i18n.js";

export const CHANGES = ["create_obligation", "mark_done", "snooze", "update_obligation"];
const CATEGORY_ICON = {
  motor_insurance: "car", health_insurance: "heart", life_insurance: "shield", electricity_bill: "bolt",
  water_bill: "droplet", gas_bill: "flame", school_fee: "school", college_fee: "school", property_tax: "home",
  certificate_renewal: "doc", other: "doc",
};

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const icon = (name) => `<svg class="ic" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const locale = () => (getLang() === "hi" ? "hi-IN" : "en-IN");
const day = (iso) => new Date(`${iso}T00:00:00`);

export const money = (n) => (n == null ? "" : `₹${Math.round(n).toLocaleString("en-IN")}`);
export const dateLong = (iso) => (iso ? day(iso).toLocaleDateString(locale(), { day: "numeric", month: "long", year: "numeric" }) : "");
export const dateShort = (iso) => (iso ? day(iso).toLocaleDateString(locale(), { day: "numeric", month: "short" }) : "");
export const daysBetween = (todayIso, iso) => Math.round((day(iso) - day(todayIso)) / 86400000);
export const addDays = (iso, n) => {
  const d = day(iso);
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
const when = (isoTime) => new Date(isoTime).toLocaleString(locale(), { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
const name = (o) => (getLang() === "hi" ? o.title_hi || o.title : o.title || o.title_hi) || "";

export function badge(today, iso) {
  if (!today || !iso) return "";
  const n = daysBetween(today, iso);
  const tone = n <= 7 ? "red" : n <= 30 ? "amber" : "";
  return `<span class="badge ${tone}">${esc(t("days_left", n))}</span>`;
}

// ---------- progress ----------
const STEPS = {
  photo: ["sent", "reading_photo", "ready"],
  voice: ["sent", "listening", "reading_text", "ready"],
  text: ["sent", "reading_text", "ready"],
};
export function steps(kind, stage, done = false) {
  const order = STEPS[kind] || STEPS.text;
  const now = done ? order.length : Math.max(0, order.findIndex((s) => s === stage || s.startsWith(stage)));
  return order.map((s, i) => {
    const cls = i < now ? "done" : i === now ? "now" : "";
    return `<li class="step ${cls}"${i === now ? ' aria-current="step"' : ""}><span class="dot">${i < now ? icon("check") : ""}</span>${esc(t(`step_${s}`))}</li>`;
  }).join("");
}

// ---------- the card ----------
function field(i, key, label, value, type, flagged, evidence, cls = "") {
  const extra = type === "number" ? ' inputmode="numeric" min="0" step="1"' : "";
  return `<label class="f ${cls} ${flagged ? "flag" : ""}"><span class="lbl">${esc(label)}${flagged ? ` · <em>${esc(t("check_this"))}</em>` : ""}</span>
    ${cls === "money" ? '<span class="money-row"><span class="cur" aria-hidden="true">₹</span>' : ""}<input data-i="${i}" data-k="${key}" type="${type}" value="${esc(value ?? "")}"${extra}>${cls === "money" ? "</span>" : ""}
    ${evidence ? `<small class="ev">${esc(t("on_paper"))}: <q>${esc(evidence)}</q></small>` : ""}</label>`;
}

function action(a, i, today) {
  const n = esc(name(a));
  if (a.tool === "create_obligation") {
    const flag = (k) => (a.needs_check || []).includes(k);
    const titleKey = getLang() === "hi" ? "title_hi" : "title";
    return `<div class="act create">
      <h3>${icon(CATEGORY_ICON[a.category] || "doc")}${n}</h3>
      ${field(i, "amount_inr", t("f_amount"), a.amount_inr, "number", flag("amount_inr"), a.evidence_amount, "money")}
      ${field(i, "due_date", t("f_due"), a.due_date, "date", flag("due_date"), a.evidence_due_date, "date")}
      ${a.due_date ? `<div class="due-line">${badge(today, a.due_date)}<span>${esc(dateLong(a.due_date))}</span></div>` : ""}
      ${field(i, "action", t("f_action"), a.action, "text", false, "")}
      ${a.consequence ? `<p class="cons"><span class="lbl">${esc(t("f_if_missed"))}</span>${esc(a.consequence)}${a.evidence_consequence ? `<small class="ev">${esc(t("on_paper"))}: <q>${esc(a.evidence_consequence)}</q></small>` : ""}</p>` : ""}
      ${field(i, titleKey, t("f_name"), a[titleKey] || name(a), "text", false, "")}
      <label class="check"><input type="checkbox" data-i="${i}" data-k="escalate" ${a.escalate ? "checked" : ""}>${esc(t("escalate"))}</label>
      <p class="plan">${icon("bell")}${esc(t("plan", a.remind_offsets_days || []))}</p></div>`;
  }
  if (a.tool === "mark_done") return `<p class="act line">${icon("check")}${esc(t("done_act", name(a)))}</p>`;
  if (a.tool === "snooze") return `<p class="act line">${icon("clock")}${esc(t("snooze_act", name(a), dateLong(a.until)))}</p>`;
  if (a.tool === "update_obligation") {
    const bits = [a.amount_inr ? t("new_amount", money(a.amount_inr)) : "", a.due_date ? t("new_date", dateLong(a.due_date)) : ""].filter(Boolean).join(", ");
    return `<p class="act line">${icon("repeat")}${esc(t("update_act", name(a), bits))}</p>`;
  }
  if (a.tool === "answer") return `<p class="act answer">${esc(pick(a, "text"))}</p>`;
  return `<p class="act clarify">${esc(pick(a, "question"))}</p>`;
}

function scamBlock(scam) {
  if (!scam || scam.level === "none") return "";
  const lang = getLang();
  const signs = (scam.signs || []).map((s) => `<li><b>${esc(s[lang] || s.en)}</b><q>${esc(s.evidence)}</q></li>`).join("");
  return `<div class="stamp-block ${esc(scam.level)}" role="alert">
    <p class="stamp">${icon("shield-alert")}${esc(t(scam.level === "warning" ? "scam_warning" : "scam_caution"))}</p>
    ${signs ? `<ul class="signs" aria-label="${esc(t("scam_signs"))}">${signs}</ul>` : ""}
    ${scam.level === "warning" ? `<p class="advice">${esc(t("scam_advice"))}</p>` : ""}</div>`;
}

export function card(c, today, { toldSon = false } = {}) {
  const changes = c.actions.some((a) => CHANGES.includes(a.tool));
  const level = c.scam?.level || "none";
  const play = `<button type="button" id="c-play" class="btn quiet">${icon("play")}${esc(t("replay"))}</button>`;
  const son = `<button type="button" id="c-son" class="btn secondary"${toldSon ? " disabled" : ""}>${esc(t(toldSon ? "told_son" : "tell_son"))}</button>`;
  let btns;
  if (level === "warning") {
    btns = `<button type="button" id="c-no" class="btn warn">${esc(t("dont_save"))}</button>${son}
      ${changes ? `<button type="button" id="c-ok" class="btn quiet">${esc(t("save_anyway"))}</button>` : ""}${play}`;
  } else if (changes) {
    btns = `<button type="button" id="c-ok" class="btn primary">${icon("check")}${esc(t("confirm"))}</button>
      <button type="button" id="c-edit" class="btn secondary">${esc(t("edit"))}</button>${level === "caution" ? son : ""}${play}
      <button type="button" id="c-no" class="btn quiet">${esc(t("discard"))}</button>`;
  } else {
    btns = `${play}${level === "caution" ? son : ""}<button type="button" id="c-no" class="btn primary">${esc(t("ok"))}</button>`;
  }
  const summary = pick(c, "summary");
  return `${scamBlock(c.scam)}
    ${c.transcript ? `<p class="said"><span class="lbl">${esc(t("you_said"))}</span><q>${esc(c.transcript)}</q></p>` : ""}
    ${summary ? `<p class="summary">${esc(summary)}</p>` : ""}
    ${c.actions.map((a, i) => action(a, i, today)).join("")}
    <div class="slip-btns">${btns}</div>`;
}

// ---------- what's next ----------
export function items(data) {
  const obs = data.obligations || [];
  if (!obs.length) return `<li class="empty">${esc(t("empty_items"))}</li>`;
  const sorted = [...obs.filter((o) => o.status !== "done"), ...obs.filter((o) => o.status === "done")];
  return sorted.map((o) => {
    const d = day(o.due_date);
    const amount = o.amount_inr != null
      ? `<span class="amt">${esc(money(o.amount_inr))}</span>`
      : o.last_amount_inr != null ? `<span class="item-meta">${esc(t("amount_unknown"))}</span>` : "";
    const next = o.next && o.status === "active"
      ? `<p class="next">${icon("bell")}${esc(t("next_reminder", t(`label_${o.next.label}`), when(o.next.at)))}</p>` : "";
    const btns = o.status === "active"
      ? `<div class="item-btns"><button type="button" class="btn primary" data-done="${esc(o.id)}">${icon("check")}${esc(t("mark_done"))}</button>
         <button type="button" class="btn secondary" data-later="${esc(o.id)}">${icon("clock")}${esc(t("later"))}</button></div>` : "";
    return `<li class="item ${esc(o.status)}">
      <div class="dateblock" aria-hidden="true"><b>${d.getDate()}</b><span>${esc(d.toLocaleDateString(locale(), { month: "short" }))}</span></div>
      <div class="item-body">
        <div class="item-top"><span class="item-name">${icon(CATEGORY_ICON[o.category] || "doc")}${esc(name(o))}</span>${amount}</div>
        <div class="item-meta">${o.status === "done" ? `<span class="tag">${icon("check")}${esc(t("done_status"))}</span>` : badge(data.today, o.due_date)}
          <span>${esc(dateLong(o.due_date))}</span>
          ${o.yearly ? `<span class="tag">${icon("repeat")}${esc(t("every_year"))}</span>` : ""}
          ${o.amount_inr == null && o.last_amount_inr != null ? `<span>${esc(t("last_year", money(o.last_amount_inr)))}</span>` : ""}</div>
        ${next}${btns}
      </div></li>`;
  }).join("");
}

// ---------- inbox ----------
export function inbox(data, role) {
  const notes = data.inbox || [];
  if (!notes.length) return `<li class="empty">${esc(t(role === "son" ? "empty_inbox_son" : "empty_inbox_parent"))}</li>`;
  const ICON = { escalation: "alert", scam_warning: "shield-alert" };
  return notes.map((n) => `<li class="note ${esc(n.kind)} ${n.read ? "read" : ""}">${icon(ICON[n.kind] || "bell")}
    <div class="note-body"><p>${esc(pick(n, "text"))}</p>
      <div class="note-btns"><button type="button" class="btn quiet small" data-play="${esc(n.id)}">${icon("play")}${esc(t("listen"))}</button>
      ${n.read ? "" : `<button type="button" class="btn quiet small" data-read="${esc(n.id)}">${icon("check")}${esc(t("mark_read"))}</button>`}</div>
    </div></li>`).join("");
}

// ---------- sheets ----------
const close = `<button type="button" class="sheet-x" data-close aria-label="${esc(t("close"))}">${icon("x")}</button>`;

export function laterSheet(id, today) {
  const chip = (n, key) => `<button type="button" class="chip-btn" data-until="${addDays(today, n)}" aria-pressed="false">${esc(t(key))}</button>`;
  return `${close}<h2 id="sheet-title">${esc(t("later_title"))}</h2>
    <div class="chips">${chip(1, "later_tomorrow")}${chip(3, "later_3")}${chip(7, "later_week")}</div>
    <label class="pick">${esc(t("later_pick"))}<input type="date" id="later-date" min="${esc(addDays(today, 1))}"></label>
    <div class="sheet-btns"><button type="button" class="btn quiet" data-close>${esc(t("discard"))}</button>
      <button type="button" class="btn primary" data-later-ok="${esc(id)}">${esc(t("later_ok"))}</button></div>`;
}

export function repeatSheet(offer) {
  return `${close}<h2 id="sheet-title">${esc(t("repeat_title"))}</h2>
    <p>${esc(t("repeat_sub", dateLong(offer.due_date)))}</p>
    <div class="sheet-btns"><button type="button" class="btn quiet" data-close>${esc(t("repeat_no"))}</button>
      <button type="button" class="btn primary" data-repeat="${esc(offer.obligation_id)}">${icon("repeat")}${esc(t("repeat_yes"))}</button></div>`;
}
