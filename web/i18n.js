// Every word the app shows, in English and Hindi. English is the default; the choice is saved per device.
const SAVED = "kaagaz.lang";
export const LANGS = ["en", "hi"];

const en = {
  brand_sub: "Papers, handled",
  lang_label: "Language", role_label: "Who is using this?", role_parent: "Papa", role_son: "Son",
  mode_demo: "Demo mode. Use the sample papers, not real documents.",
  mode_real: "Private mode. Photos and voice stay on this computer.",
  intro_title: "How Kaagaz helps",
  intro_1: "Show a paper or a message", intro_2: "Kaagaz explains it and checks it for scams",
  intro_3: "It reminds Papa, and tells his son if it slips", intro_close: "Got it",
  hello_parent: "Hello Papa", hello_son: "Hello",
  count: (n) => (n === 0 ? "Nothing due right now" : n === 1 ? "1 thing coming up" : `${n} things coming up`),
  speak: "Hold to speak", speak_hint: "or tap once, then tap again to send",
  speak_hold: "Listening… let go to send", speak_tap: "Listening… tap to send",
  scan: "Scan a paper", scan_sub: "Bill, notice or message",
  type: "Type a question", type_sub: "“When is the bill due?”",
  ask_placeholder: "e.g. When is the electricity bill due?", send: "Send",
  mic_denied: "Microphone permission was not given. You can type your question instead.",
  heard_nothing: "I didn't hear anything — please speak again.",
  step_sent: "Sent", step_listening: "Listening", step_reading_photo: "Reading & checking for scams",
  step_reading_text: "Understanding", step_ready: "Your card",
  too_slow: "This is taking too long — please try again.", failed: "Something went wrong — please try again.",
  network: "Couldn't reach the server — check the internet.",
  you_said: "You said", on_paper: "On the paper", check_this: "please check this on the paper",
  f_name: "Name", f_amount: "Amount (₹)", f_due: "Due date", f_action: "What to do", f_if_missed: "If missed",
  escalate: "Tell my son if I forget",
  plan: (days) => `Reminders: ${days.map((d) => `${d} day${d === 1 ? "" : "s"} before`).join(", ")}`,
  confirm: "Yes, save it", edit: "Edit", discard: "Discard", ok: "OK", replay: "Listen again",
  scam_warning: "This doesn't look genuine", scam_caution: "Be careful with this one",
  scam_advice: "Don't pay, don't call, and don't share an OTP. Check with the number on an old bill, or ask your son.",
  dont_save: "Don't save", save_anyway: "Save anyway", tell_son: "Tell my son", told_son: "Your son has been told ✓",
  done_act: (n) => `${n} — done`, snooze_act: (n, d) => `${n} — I'll remind you again on ${d}`,
  update_act: (n, bits) => `${n} — ${bits}`, new_amount: (a) => `new amount ${a}`, new_date: (d) => `new date ${d}`,
  saved: "Saved — I'll remind you ✓",
  next_title: "What's next", empty_items: "Nothing yet. Show a paper or speak to add one.",
  days_left: (n) => (n < 0 ? `${-n} days late` : n === 0 ? "Due today" : n === 1 ? "1 day left" : `${n} days left`),
  days_unit: "days", today_unit: "today", late_unit: "late",
  every_year: "Every year", last_year: (a) => `Last year ${a}`, amount_unknown: "Amount not known yet",
  next_reminder: (label, when) => `Next: ${label} · ${when}`, done_status: "Done",
  mark_done: "Done", later: "Later", done_toast: "Well done — marked done ✓",
  later_title: "Remind me again", later_tomorrow: "Tomorrow", later_3: "In 3 days", later_week: "Next week",
  later_pick: "Pick a date", later_ok: "Remind me", pick_date: "Please pick a date.",
  snoozed: (d) => `I'll remind you again on ${d} ✓`,
  repeat_title: "Remind you again next year?", repeat_sub: (d) => `Same paper, due ${d}`,
  repeat_yes: "Yes, next year too", repeat_no: "No thanks", repeat_saved: (d) => `Added for ${d} ✓`,
  inbox_title: "Inbox", empty_inbox_parent: "No reminders yet.", empty_inbox_son: "No alerts. All is well.",
  listen: "Listen", mark_read: "Mark read",
  push_on: "Turn on phone notifications", push_done_parent: "Notifications on for Papa's phone ✓",
  push_done_son: "Notifications on for the son's phone ✓",
  push_unsupported: "This browser can't show phone notifications — everything still shows here. (iPhone: add to Home Screen first.)",
  push_unavailable: "Phone notifications aren't available right now — everything shows here.",
  push_denied: "Permission not given — everything still shows here.",
  samples_title: "Try a sample", samples_sub: "Fictitious papers and messages",
  s_motor_renewal: "Car insurance", s_electricity_bill: "Electricity bill", s_school_fee: "School fee",
  s_property_tax: "Property tax", s_scam_sms: "Suspicious SMS", s_scam_whatsapp: "WhatsApp prize",
  waking: "Waking up the assistant", waking_sub: "It runs on a free server — about a minute after a quiet spell.",
  waking_failed: "The server didn't wake up. Please open the page again in a little while.",
  how: "How it works", close: "Close", unread: (n) => `${n} unread`, steps_label: "Progress",
  scam_signs: "Warning signs on it", lang_en: "English", lang_hi: "Hindi", theme_dark: "Dark mode",
  label_d30: "30 days before", label_d7: "7 days before", label_d1: "1 day before", label_now: "now",
  label_snooze: "your chosen date", label_escalation: "tell the son",
};

const hi = {
  brand_sub: "काग़ज़ों का साथी",
  lang_label: "भाषा", role_label: "कौन इस्तेमाल कर रहा है?", role_parent: "पापा", role_son: "बेटा",
  mode_demo: "डेमो मोड। असली काग़ज़ नहीं, नमूने आज़माइए।",
  mode_real: "निजी मोड। फ़ोटो और आवाज़ इसी कंप्यूटर पर रहती है।",
  intro_title: "काग़ज़ कैसे मदद करता है",
  intro_1: "काग़ज़ या मैसेज दिखाइए", intro_2: "काग़ज़ उसे समझाता है और धोखे की जाँच करता है",
  intro_3: "पापा को याद दिलाता है, और छूट जाए तो बेटे को बताता है", intro_close: "समझ गया",
  hello_parent: "नमस्ते पापा", hello_son: "नमस्ते",
  count: (n) => (n === 0 ? "अभी कुछ बाकी नहीं" : `${n} काम आने वाले हैं`),
  speak: "दबाकर बोलिए", speak_hint: "या एक बार दबाइए, भेजने के लिए फिर दबाइए",
  speak_hold: "सुन रहा हूँ… छोड़िए तो भेजूँ", speak_tap: "सुन रहा हूँ… भेजने के लिए दबाइए",
  scan: "काग़ज़ दिखाइए", scan_sub: "बिल, नोटिस या मैसेज",
  type: "लिखकर पूछिए", type_sub: "“बिल कब भरना है?”",
  ask_placeholder: "जैसे: बिजली का बिल कब तक भरना है?", send: "भेजें",
  mic_denied: "माइक की अनुमति नहीं मिली। आप लिखकर भी पूछ सकते हैं।",
  heard_nothing: "कुछ सुनाई नहीं दिया — फिर से बोलिए।",
  step_sent: "भेजा", step_listening: "सुन रहा हूँ", step_reading_photo: "पढ़ रहा हूँ, धोखे की जाँच भी",
  step_reading_text: "समझ रहा हूँ", step_ready: "आपका कार्ड",
  too_slow: "बहुत देर लग रही है — फिर से कोशिश करें।", failed: "कुछ गड़बड़ हुई — फिर से कोशिश करें।",
  network: "सर्वर से जुड़ नहीं पाए — इंटरनेट देखिए।",
  you_said: "आपने कहा", on_paper: "काग़ज़ पर", check_this: "काग़ज़ पर देखकर पक्का कीजिए",
  f_name: "नाम", f_amount: "रकम (₹)", f_due: "आख़िरी तारीख़", f_action: "क्या करना है", f_if_missed: "न करने पर",
  escalate: "अगर मैं भूल जाऊँ तो बेटे को बताना",
  plan: (days) => `याद दिलाऊँगा: ${days.map((d) => `${d} दिन पहले`).join(", ")}`,
  confirm: "सही है, सेव करो", edit: "बदलें", discard: "रद्द", ok: "ठीक है", replay: "फिर सुनिए",
  scam_warning: "यह असली नहीं लगता", scam_caution: "इसमें सावधानी रखिए",
  scam_advice: "पैसे मत भेजिए, फ़ोन मत कीजिए, OTP मत बताइए। पुराने बिल पर लिखे नंबर से पता कीजिए, या बेटे से पूछिए।",
  dont_save: "सेव मत करो", save_anyway: "फिर भी सेव करो", tell_son: "बेटे को बताओ", told_son: "बेटे को बता दिया ✓",
  done_act: (n) => `${n} — हो गया`, snooze_act: (n, d) => `${n} — ${d} को फिर याद दिलाऊँगा`,
  update_act: (n, bits) => `${n} — ${bits}`, new_amount: (a) => `नई रकम ${a}`, new_date: (d) => `नई तारीख़ ${d}`,
  saved: "सेव हो गया — मैं याद दिलाऊँगा ✓",
  next_title: "आगे क्या है", empty_items: "अभी कुछ नहीं। काग़ज़ दिखाइए या बोलिए।",
  days_left: (n) => (n < 0 ? `${-n} दिन देर` : n === 0 ? "आज आख़िरी दिन" : `${n} दिन बचे`),
  days_unit: "दिन", today_unit: "आज", late_unit: "देर",
  every_year: "हर साल", last_year: (a) => `पिछले साल ${a}`, amount_unknown: "रकम अभी पता नहीं",
  next_reminder: (label, when) => `अगला: ${label} · ${when}`, done_status: "हो गया",
  mark_done: "हो गया", later: "बाद में", done_toast: "बहुत बढ़िया — हो गया ✓",
  later_title: "फिर कब याद दिलाऊँ", later_tomorrow: "कल", later_3: "3 दिन बाद", later_week: "अगले हफ़्ते",
  later_pick: "तारीख़ चुनिए", later_ok: "याद दिलाना", pick_date: "तारीख़ चुनिए।",
  snoozed: (d) => `${d} को फिर याद दिलाऊँगा ✓`,
  repeat_title: "अगले साल फिर याद दिलाऊँ?", repeat_sub: (d) => `यही काग़ज़, आख़िरी तारीख़ ${d}`,
  repeat_yes: "हाँ, अगले साल भी", repeat_no: "नहीं", repeat_saved: (d) => `${d} के लिए जोड़ दिया ✓`,
  inbox_title: "सूचनाएँ", empty_inbox_parent: "अभी कोई reminder नहीं।", empty_inbox_son: "कोई चेतावनी नहीं। सब ठीक है।",
  listen: "सुनिए", mark_read: "पढ़ लिया",
  push_on: "फ़ोन पर सूचना चालू करें", push_done_parent: "पापा के फ़ोन पर सूचना चालू ✓",
  push_done_son: "बेटे के फ़ोन पर सूचना चालू ✓",
  push_unsupported: "इस ब्राउज़र में फ़ोन सूचना नहीं चलती — सब कुछ यहीं दिखेगा। (iPhone: पहले Home Screen पर जोड़ें)",
  push_unavailable: "फ़ोन सूचना अभी उपलब्ध नहीं — सब कुछ यहीं दिखेगा।",
  push_denied: "अनुमति नहीं मिली — सब कुछ यहीं दिखता रहेगा।",
  samples_title: "नमूना आज़माइए", samples_sub: "काल्पनिक काग़ज़ और मैसेज",
  s_motor_renewal: "गाड़ी का बीमा", s_electricity_bill: "बिजली का बिल", s_school_fee: "स्कूल फ़ीस",
  s_property_tax: "प्रॉपर्टी टैक्स", s_scam_sms: "संदिग्ध SMS", s_scam_whatsapp: "WhatsApp इनाम",
  waking: "सहायक जाग रहा है", waking_sub: "यह मुफ़्त सर्वर पर चलता है — कुछ देर बाद खोलने पर लगभग एक मिनट।",
  waking_failed: "सर्वर नहीं जागा — थोड़ी देर बाद पेज फिर खोलिए।",
  how: "यह कैसे काम करता है", close: "बंद करें", unread: (n) => `${n} नई`, steps_label: "कहाँ तक पहुँचा",
  scam_signs: "इसमें धोखे के निशान", lang_en: "अंग्रेज़ी", lang_hi: "हिंदी", theme_dark: "डार्क मोड",
  label_d30: "30 दिन पहले वाला", label_d7: "7 दिन पहले वाला", label_d1: "1 दिन पहले वाला", label_now: "अभी",
  label_snooze: "आपकी बताई तारीख़ वाला", label_escalation: "बेटे को सूचना",
};

export const TABLE = { en, hi };
let lang = (() => {
  const q = new URLSearchParams(location.search).get("lang");
  if (LANGS.includes(q)) return q;
  try { const s = localStorage.getItem(SAVED); if (LANGS.includes(s)) return s; } catch { /* private mode */ }
  return "en";
})();

export const getLang = () => lang;
export function setLang(l) {
  if (!LANGS.includes(l)) return;
  lang = l;
  try { localStorage.setItem(SAVED, l); } catch { /* private mode */ }
  document.documentElement.lang = l;
}
export function t(key, ...args) {
  const v = TABLE[lang][key] ?? TABLE.en[key] ?? key;
  return typeof v === "function" ? v(...args) : v;
}
// Server messages come as {code, en, hi}; model text as paired fields (text_en / text_hi).
export const pick = (o, base) => (o ? o[`${base}_${lang}`] || o[`${base}_hi`] || o[`${base}_en`] || "" : "");
export function errorText(detail, fallback) {
  if (detail && typeof detail === "object" && !Array.isArray(detail) && (detail.en || detail.hi)) return detail[lang] || detail.en;
  if (typeof detail === "string") return detail;
  return fallback;
}
