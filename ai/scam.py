"""Scam warning signs. The model proposes signs, each with the exact words that triggered it; this module keeps
only signs whose words really show what the sign claims, and grades them. It never says "safe"."""
import re

SCAM_SIGNS = ["personal_payment", "suspicious_link", "asks_secret", "remote_app", "threat_deadline", "call_number",
              "prize_refund"]

MOBILE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
UPI = re.compile(r"[\w.\-]{2,}@[A-Za-z]{2,}(?![\w.@])")          # x@ybl, not care@board.in
ACCOUNT = re.compile(r"(?i)(?:a/c|account|खाता)\D{0,15}\d{6,}")
PAY = re.compile(r"(?i)\b(?:pay|send|transfer|upi|phonepe|gpay|google pay|paytm)\b|भेज|भुगतान|पेमेंट|जमा")
LINK = re.compile(r"(?i)https?://\S+|www\.\S+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|in|net|org|xyz|top|info|link|ly|me"
                  r"|co|site|online|live|click|app|gd)\b")
# Shorteners, unusual endings and bare IPs: genuine bills print their own portal, these they don't.
SHADY_LINK = re.compile(r"(?i)bit\.ly|tinyurl|goo\.gl|cutt\.ly|t\.ly|rb\.gy|is\.gd|shorturl"
                        r"|\.(?:xyz|top|info|link|site|online|live|click|app)\b|https?://\d+\.\d+\.\d+\.\d+")
SECRET = re.compile(r"(?i)\b(?:otp|pin|cvv|password)\b|ओटीपी|पिन|पासवर्ड")
# "We never ask for your OTP" / "OTP किसी को न बताएं" is the bill protecting him, not asking; "PIN 452001" is a postcode.
NEG_BEFORE = re.compile(r"(?i)\b(?:never|not|don't|do not|won't|will not|no one)\b|नहीं|मत|कभी")
NEG_AFTER = re.compile(r"(?<![ऀ-ॿ])(?:न|नहीं|मत)(?![ऀ-ॿ])")
POSTCODE = re.compile(r"(?i)pin(?:\s*code)?\s*(?:no\.?)?\s*[:\-]?\s*\d{6}|pin\s*code")
REMOTE = re.compile(r"(?i)any\s?desk|team\s?viewer|quick\s?support|\.apk\b|एनीडेस्क")
# Hindi words need Devanagari-aware edges: रात must not match inside गुजरात or रात्रि. A clock time alone is office
# hours, and "आज ही भुगतान करें" is a normal bill line, so neither counts.
THREAT = re.compile(r"(?i)\btonight\b|\btoday\b|within\s+\d+\s*(?:hours?|hrs?|minutes?|mins?)"
                    r"|(?<![ऀ-ॿ])(?:घंटे|रात)(?![ऀ-ॿ])")
PRIZE = re.compile(r"(?i)prize|lottery|lucky|\bdraw\b|\bwon\b|winner|bonus|refund|cashback|reward|kyc"
                   r"|इनाम|लॉटरी|रिफंड|रिफ़ंड|बोनस|कैशबैक")
# Printed on genuine policies and bills: an insurance No Claim Bonus, card reward points, a deposit refund.
NOT_PRIZE = re.compile(r"(?i)no[\s-]*claim\s*bonus|\bncb\b|reward\s*points?|(?:security\s*)?deposit\s*refund"
                       r"|refund\s*of\s*(?:security\s*)?deposit")


def _asks_secret(ev: str) -> bool:
    for m in SECRET.finditer(ev):
        if NEG_BEFORE.search(ev[max(0, m.start() - 40):m.start()]) or NEG_AFTER.search(ev[m.end():m.end() + 25]):
            continue
        if POSTCODE.match(ev, m.start()):
            continue
        return True
    return False


CHECKS = {
    "personal_payment": lambda ev: bool(UPI.search(ev) or ACCOUNT.search(ev) or (MOBILE.search(ev) and PAY.search(ev))),
    "suspicious_link": lambda ev: bool(LINK.search(ev)),
    "asks_secret": _asks_secret,
    "remote_app": lambda ev: bool(REMOTE.search(ev)),
    "threat_deadline": lambda ev: bool(THREAT.search(ev)),
    "call_number": lambda ev: bool(MOBILE.search(ev)),
    "prize_refund": lambda ev: bool(PRIZE.search(NOT_PRIZE.sub(" ", ev))),
}
ALWAYS_STRONG = {"personal_payment", "asks_secret", "remote_app", "prize_refund"}

LABELS = {
    "personal_payment": ("Asks you to pay a personal UPI ID, number or account",
                         "किसी निजी UPI, नंबर या खाते में पैसे माँगता है"),
    "suspicious_link": ("Has a link to pay or 'update' details", "पैसे भरने या जानकारी 'अपडेट' करने का लिंक है"),
    "asks_secret": ("Asks for an OTP, PIN or password", "OTP, PIN या पासवर्ड माँगता है"),
    "remote_app": ("Asks you to install an app like AnyDesk", "AnyDesk जैसा ऐप डालने को कहता है"),
    "threat_deadline": ("Threatens action within hours", "कुछ ही घंटों में कार्रवाई की धमकी देता है"),
    "call_number": ("Asks you to call a mobile number", "किसी मोबाइल नंबर पर फ़ोन करने को कहता है"),
    "prize_refund": ("Promises a prize, bonus or refund", "इनाम, बोनस या रिफ़ंड का लालच देता है"),
}
SPOKEN = {
    "warning": ("Careful — this doesn't look genuine. Don't pay, don't call the number in it, and don't share an OTP. "
                "Only save it if you're sure it's real.",
                "सावधान — यह असली नहीं लगता। पैसे मत भेजिए, इसमें दिए नंबर पर फ़ोन मत कीजिए, OTP मत बताइए। "
                "पक्का हो तभी सेव कीजिए।"),
    "caution": ("Be careful with this one.", "इसमें सावधानी रखिए।"),
}


def _strong(sign: str, evidence: str, doc_type: str | None) -> bool:
    if sign == "personal_payment" and doc_type == "bill_or_notice":
        return False   # genuine bills print their own account number or UPI ID: on a paper it's amber, not red
    if sign in ALWAYS_STRONG:
        return True
    return sign == "suspicious_link" and bool(SHADY_LINK.search(evidence))


def check_signs(raw, doc_type: str | None = None) -> list[dict]:
    signs, seen = [], set()
    for s in raw if isinstance(raw, list) else []:
        if not isinstance(s, dict):
            continue
        sign, evidence = s.get("sign"), str(s.get("evidence") or "").strip()
        if sign not in CHECKS or sign in seen or not evidence or not CHECKS[sign](evidence):
            continue
        seen.add(sign)
        signs.append({"sign": sign, "evidence": evidence[:200], "strong": _strong(sign, evidence, doc_type)})
    return signs


def level(signs: list[dict]) -> str:
    if any(s["strong"] for s in signs):
        return "warning"
    if {"threat_deadline", "call_number"} <= {s["sign"] for s in signs}:
        return "warning"
    return "caution" if signs else "none"


def scam_summary(signs: list[dict]) -> dict:
    return {"level": level(signs),
            "signs": [{**s, "en": LABELS[s["sign"]][0], "hi": LABELS[s["sign"]][1]} for s in signs]}
