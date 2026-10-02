"""Fictitious eval documents and their ground truth, from one table so the two can't drift.

  python -m eval.make_docs
Writes eval/papers/<id>.html and updates the "papers" section of eval/ground_truth.json. Everything here is
invented: names, numbers, organisations, links. Phone numbers use the common 98765 dummy pattern."""
import json
from pathlib import Path

ROOT = Path(__file__).parent

PAPER = """<!doctype html><html><head><meta charset="utf-8"><style>
body{{font-family:"Nirmala UI",Arial,sans-serif;width:744px;margin:0;padding:28px;background:#fffef6;color:#111;font-size:14px;line-height:1.45}}
.hd{{text-align:center;border:2px solid #333;padding:8px;margin-bottom:10px}}.t1{{font-size:19px;font-weight:bold}}.t2{{font-size:12px}}
table{{width:100%;border-collapse:collapse;margin:8px 0}}td{{border:1px solid #666;padding:5px 7px}}.k{{background:#f1f1e4;width:36%}}
.big{{font-size:20px;font-weight:bold}}.box{{border:2px solid #000;padding:8px;margin:10px 0}}
.wm{{position:absolute;top:420px;left:140px;font-size:90px;color:rgba(0,0,0,.06);transform:rotate(-25deg)}}
.ft{{font-size:11px;margin-top:14px;color:#444}}
</style></head><body><div class="wm">SPECIMEN</div>{body}
<div class="ft">SPECIMEN DOCUMENT — FICTITIOUS DATA / नमूना दस्तावेज़ — काल्पनिक</div></body></html>"""

PHONE = """<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;width:400px;font-family:"Segoe UI","Nirmala UI",Arial,sans-serif;background:{bg};}}
.bar{{background:{bar};color:{barfg};padding:14px 16px;font-size:16px;font-weight:600}}.bar small{{display:block;font-weight:400;font-size:12px;opacity:.8}}
.thread{{padding:16px 12px 40px}}.b{{background:{bubble};color:#111;border-radius:14px;padding:10px 12px;font-size:15px;line-height:1.45;max-width:320px;box-shadow:0 1px 1px rgba(0,0,0,.12)}}
.ts{{font-size:11px;color:#667;margin:6px 4px}}.spec{{font-size:10px;color:#889;text-align:center;margin-top:24px}}
</style></head><body><div class="bar">{sender}<small>{sub}</small></div><div class="thread">
<div class="ts">{time}</div><div class="b">{body}</div><div class="spec">SPECIMEN — FICTITIOUS MESSAGE</div></div></body></html>"""

SMS = {"bg": "#ffffff", "bar": "#f2f2f7", "barfg": "#111", "bubble": "#e9e9eb"}
WHATSAPP = {"bg": "#efe7dd", "bar": "#075e54", "barfg": "#fff", "bubble": "#ffffff"}


def paper(header: str, sub: str, rows: list[tuple[str, str]], box: str, note: str) -> str:
    table = "".join(f'<tr><td class="k">{k}</td><td>{v}</td></tr>' for k, v in rows)
    return PAPER.format(body=f'<div class="hd"><div class="t1">{header}</div><div class="t2">{sub}</div></div>'
                             f'<table>{table}</table>{box}<p>{note}</p>')


def phone(style: dict, sender: str, sub: str, time: str, body: str) -> str:
    return PHONE.format(**style, sender=sender, sub=sub, time=time, body=body)


def truth(category, amount, due, keywords=(), scam_level=("none",), scam_signs=()):
    return {"category": category, "amount_inr": amount, "due_date": due, "consequence_keywords": list(keywords),
            "scam_level": list(scam_level), "scam_signs": list(scam_signs)}


DOCS = [
    # ---------- genuine papers ----------
    {"id": "water_bill_hi", "kind": "paper", "html": paper(
        "नगर जल प्रदाय विभाग (नमूना)", "जल बिल — त्रैमासिक",
        [("उपभोक्ता क्रमांक", "W-20419"), ("नाम", "सुरेश प्रसाद"), ("बिल दिनांक", "22-09-2026"),
         ("अवधि", "जुलाई – सितंबर 2026"), ("खपत", "18 किलोलीटर")],
        '<div class="box">कुल देय राशि: <span class="big">₹ 486</span> &nbsp; | &nbsp; अंतिम तिथि: <span class="big">20-10-2026</span></div>',
        "अंतिम तिथि के बाद ₹ 50 विलंब शुल्क लगेगा तथा दो माह बकाया होने पर नल कनेक्शन विच्छेद किया जा सकता है।"),
     "truth": truth("water_bill", 486, "2026-10-20", ["50", "late", "disconnect", "विच्छेद", "विलंब"])},
    {"id": "gas_bill_en", "kind": "paper", "html": paper(
        "Shakti City Gas Distribution Ltd (Specimen)", "Piped Natural Gas — Domestic Bill",
        [("BP Number", "1100234567"), ("Customer", "Anita Verma"), ("Bill Date", "28-09-2026"),
         ("Billing Period", "26-07-2026 to 25-09-2026"), ("Consumption", "31.4 SCM")],
        '<div class="box">Amount Payable: <span class="big">₹ 1,214.00</span> &nbsp; | &nbsp; Due Date: <span class="big">12-10-2026</span></div>',
        "A late payment charge of ₹ 100 will be added for payment after the due date."),
     "truth": truth("gas_bill", 1214, "2026-10-12", ["100", "late"])},
    {"id": "health_renewal", "kind": "paper", "html": paper(
        "Aarogya Health Insurance Co. Ltd (Specimen)", "Renewal Notice — Family Floater",
        [("Policy No.", "AH/2025/778812"), ("Insured", "Sunita Sharma, Ramesh Sharma"), ("Sum Insured", "₹ 5,00,000"),
         ("Policy Period Ends", "05/11/2026"), ("Renewal Premium (incl. GST)", "₹ 23,650")],
        '<div class="box">Please renew on or before <b>05/11/2026</b>.</div>',
        "A grace period of 30 days is available. If the policy is not renewed within the grace period, continuity "
        "benefits including waiting period credit will be lost."),
     "truth": truth("health_insurance", 23650, "2026-11-05", ["waiting period", "continuity"])},
    {"id": "life_premium", "kind": "paper", "html": paper(
        "Jeevan Suraksha Life Insurance (Specimen)", "Premium Due Notice",
        [("Policy No.", "51234987"), ("Plan", "Endowment, yearly mode"), ("Policyholder", "Mohan Lal Gupta"),
         ("Premium Due Date", "20/10/2026"), ("Premium Amount", "₹ 9,800")],
        '<div class="box">Kindly pay the premium of <b>₹ 9,800</b> on or before <b>20/10/2026</b>.</div>',
        "If the premium is not paid, the policy will lapse after the grace period and the cover will stop."),
     "truth": truth("life_insurance", 9800, "2026-10-20", ["lapse"])},
    {"id": "college_fee", "kind": "paper", "html": paper(
        "Govt. Arts &amp; Science College (Specimen)", "Fee Notice — B.Sc. Second Year, Semester II",
        [("Student", "Rahul Yadav"), ("Enrolment No.", "BSC/2025/4471"), ("Semester Fee", "Rs. 42,000"),
         ("Last Date", "30 October 2026")],
        '<div class="box">Deposit <b>Rs. 42,000</b> by <b>30 October 2026</b>.</div>',
        "A late fine of Rs. 100 per day will be charged after the last date. Students who do not pay by "
        "15 November 2026 will not be allowed to sit in the examination."),
     "truth": truth("college_fee", 42000, "2026-10-30", ["100", "fine", "examination"])},
    {"id": "dl_renewal", "kind": "paper", "html": paper(
        "Regional Transport Office (Specimen)", "Driving Licence Renewal Reminder",
        [("DL No.", "MP09 20160012345"), ("Holder", "Prakash Joshi"), ("Valid Till (Non-Transport)", "18-11-2026"),
         ("Total Renewal Fee", "₹ 600 (renewal ₹ 400 + smart card ₹ 200)")],
        '<div class="box">Renew before <b>18-11-2026</b>.</div>',
        "Driving with an expired licence attracts a fine."),
     "truth": truth("certificate_renewal", 600, "2026-11-18", ["fine"])},
    {"id": "property_tax_hi", "kind": "paper", "html": paper(
        "नगर निगम (नमूना)", "संपत्ति कर मांग पत्र — वर्ष 2026-27",
        [("संपत्ति क्रमांक", "45/1203"), ("स्वामी", "कमला देवी"), ("कुल मांग", "₹ 8,960"), ("अंतिम तिथि", "31-12-2026")],
        '<div class="box">31-10-2026 तक भुगतान करने पर 10% छूट दी जाएगी। <b>अंतिम तिथि: 31-12-2026</b></div>',
        "अंतिम तिथि के बाद 1.5% प्रति माह अधिभार लगेगा।"),
     "truth": truth("property_tax", 8960, "2026-12-31", ["1.5", "अधिभार", "surcharge"])},
    {"id": "electricity_multi_date", "kind": "paper", "html": paper(
        "Purv Kshetra Power Supply Co (Specimen)", "Electricity Bill — September 2026",
        [("Consumer No.", "P7712004455"), ("Name", "Deepak Mishra"), ("Reading Date", "15-09-2026"),
         ("Bill Date", "18-09-2026"), ("Current Bill", "₹ 2,980"), ("Arrears", "₹ 125")],
        '<div class="box">Net Payable: <span class="big">₹ 3,105</span> &nbsp; Due Date: <span class="big">18-10-2026</span>'
        ' &nbsp; After Due Date: ₹ 3,180 &nbsp; Disconnection Date (if unpaid): 02-11-2026</div>',
        "Supply will be disconnected if the bill remains unpaid on the disconnection date. A surcharge applies after the due date."),
     "truth": truth("electricity_bill", 3105, "2026-10-18", ["disconnect"])},
    {"id": "no_due_circular", "kind": "paper", "html": paper(
        "Saraswati Vidya Mandir (Specimen)", "Circular / परिपत्र",
        [("Date", "29-09-2026"), ("To", "Parents of Classes 1–8")],
        '<div class="box">Annual Day contribution: <b>₹ 500</b> per student.</div>',
        "Dear Parents, a contribution of ₹ 500 per student is requested for the Annual Day celebration. Kindly send "
        "it with your ward at the earliest. वार्षिकोत्सव हेतु ₹ 500 का सहयोग अपेक्षित है।"),
     "truth": truth(["school_fee", "other"], 500, None)},
    {"id": "paid_receipt", "kind": "paper", "html": paper(
        "Madhya Kshetra Vidyut Vitaran (Specimen)", "Payment Receipt / भुगतान रसीद",
        [("Receipt No.", "R-88412"), ("Consumer No.", "N3409912345"), ("Amount Received", "₹ 2,346"),
         ("Payment Date", "30-09-2026"), ("Mode", "UPI"), ("Status", "SUCCESS")],
        '<div class="box">Thank you for your payment. धन्यवाद।</div>', ""),
     "truth": truth("electricity_bill", "any", None)},
    {"id": "genuine_disconnection", "kind": "paper", "html": paper(
        "Madhya Kshetra Vidyut Vitaran Nigam (Specimen)", "FINAL DISCONNECTION NOTICE / अंतिम विच्छेदन सूचना",
        [("Consumer No.", "N3409955555"), ("Name", "Harish Chandra"), ("Arrears Outstanding", "₹ 5,870"),
         ("Pay By", "09-10-2026")],
        '<div class="box">Pay <b>₹ 5,870</b> by <b>09-10-2026</b> to avoid disconnection of supply under Section 56 of the Electricity Act, 2003.</div>',
        "Pay at any cash counter or online at www.mkvvn.in. Helpline: 1912 (toll free)."),
     "truth": truth("electricity_bill", 5870, "2026-10-09", ["disconnect"], scam_level=("none", "caution"))},
    {"id": "two_wheeler", "kind": "paper", "html": paper(
        "Surakshit Bima Co. (Specimen)", "दोपहिया वाहन बीमा नवीनीकरण / Two-wheeler Insurance Renewal",
        [("Vehicle / वाहन", "MP09 AB 1234"), ("Owner / मालिक", "Vinod Kumar"),
         ("Policy Expiry / पॉलिसी समाप्ति", "02-11-2026"), ("Renewal Premium / नवीनीकरण प्रीमियम", "₹ 1,890")],
        '<div class="box">Renew by / नवीनीकरण की तिथि: <b>02-11-2026</b></div>',
        "Renewing after expiry needs a vehicle inspection. समाप्ति के बाद नवीनीकरण पर वाहन निरीक्षण आवश्यक है।"),
     "truth": truth("motor_insurance", 1890, "2026-11-02", ["inspection", "निरीक्षण"])},
    {"id": "broadband", "kind": "paper", "html": paper(
        "SwiftNet Broadband (Specimen)", "Tax Invoice INV-2026-09-55812",
        [("Account", "SN-778120"), ("Plan", "100 Mbps Unlimited"), ("Bill Period", "01-09-2026 to 30-09-2026"),
         ("Invoice Date", "01-10-2026"), ("Amount Due (incl. GST)", "₹ 1,179")],
        '<div class="box">Pay by <b>14-10-2026</b></div>',
        "Service may be suspended if the invoice remains unpaid."),
     "truth": truth("other", 1179, "2026-10-14", ["suspend"])},
    {"id": "society_maintenance", "kind": "paper", "html": paper(
        "Shanti Kunj Residents Welfare Society (Specimen)", "Maintenance Bill — Oct to Dec 2026",
        [("Flat", "B-304"), ("Member", "Meena Agarwal"), ("Maintenance", "₹ 3,500"), ("Due Date", "10-10-2026")],
        '<div class="box">Please pay <b>₹ 3,500</b> by <b>10-10-2026</b>.</div>',
        "Interest at 2% per month will be charged on late payment."),
     "truth": truth("other", 3500, "2026-10-10", ["2%", "interest"])},
    {"id": "tuition_hi", "kind": "paper", "html": paper(
        "आदर्श पब्लिक स्कूल (नमूना)", "फ़ीस सूचना — कक्षा 7",
        [("छात्र", "आयुष शर्मा"), ("तिमाही", "अक्टूबर – दिसंबर 2026"), ("फ़ीस", "₹ 6,750"), ("अंतिम तिथि", "07-10-2026")],
        '<div class="box">द्वितीय तिमाही की फ़ीस <b>₹ 6,750</b> दिनांक <b>07-10-2026</b> तक जमा करें।</div>',
        "विलंब होने पर ₹ 20 प्रतिदिन विलंब शुल्क लगेगा।"),
     "truth": truth("school_fee", 6750, "2026-10-07", ["20", "विलंब", "late"])},
    {"id": "puc_expiry", "kind": "paper", "html": paper(
        "Pollution Under Control Certificate (Specimen)", "PUC Certificate",
        [("Vehicle", "MP09 AB 1234"), ("Fuel", "Petrol"), ("Date of Test", "25-04-2026"), ("Valid Up To", "25-10-2026"),
         ("Result", "PASS")],
        '<div class="box">Valid up to <b>25-10-2026</b></div>',
        "Driving without a valid PUC certificate may attract a penalty."),
     "truth": truth("certificate_renewal", None, "2026-10-25", ["penalty"])},
    # ---------- scam messages ----------
    {"id": "scam_sms_power_cut", "kind": "phone", "html": phone(
        SMS, "+91 98765 43210", "Text Message", "Today 6:42 PM",
        "Dear consumer, your electricity power will be disconnected tonight at 9.30 pm from electricity office because "
        "your previous month bill was not update. Please immediately contact our electricity officer 98765 43210. Thank you."),
     "truth": truth("any", "any", "any", scam_level=("warning",), scam_signs=("threat_deadline", "call_number"))},
    {"id": "scam_sms_kyc_link", "kind": "phone", "html": phone(
        SMS, "AD-SBNBNK", "Text Message", "Today 10:05 AM",
        "Dear Customer, your SBN bank account will be blocked today due to pending KYC. Update your PAN immediately: "
        "http://bit.ly/kyc-sbn-upd"),
     "truth": truth("any", "any", "any", scam_level=("warning",), scam_signs=("suspicious_link", "threat_deadline"))},
    {"id": "scam_sms_challan_link", "kind": "phone", "html": phone(
        SMS, "VK-ECHLAN", "Text Message", "Yesterday 4:17 PM",
        "Your vehicle MP09AB1234 has a pending e-challan of Rs.500. Pay within 24 hours to avoid court action: "
        "https://echallan-parivahan.top/pay"),
     "truth": truth("any", "any", "any", scam_level=("warning",), scam_signs=("suspicious_link", "threat_deadline"))},
    {"id": "scam_whatsapp_lottery", "kind": "phone", "html": phone(
        WHATSAPP, "+91 98765 01234", "online", "11:31 AM",
        "🎉 Congratulations! Your WhatsApp number has won ₹25,00,000 in the KBC Lucky Draw 2026. To claim, pay the "
        "registration fee of ₹12,500 to UPI: kbcprize.claim@ybl and send the screenshot."),
     "truth": truth("any", "any", "any", scam_level=("warning",), scam_signs=("prize_refund", "personal_payment"))},
    {"id": "scam_sms_refund_otp", "kind": "phone", "html": phone(
        SMS, "+91 98765 11223", "Text Message", "Today 1:12 PM",
        "LIC: Your policy bonus refund of Rs 18,420 is approved. Our officer will call you. Share the OTP you receive "
        "to get the amount in your bank account."),
     "truth": truth("any", "any", "any", scam_level=("warning",), scam_signs=("prize_refund", "asks_secret"))},
    {"id": "scam_whatsapp_gas_hi", "kind": "phone", "html": phone(
        WHATSAPP, "Gas Seva Kendra", "+91 98765 33445", "7:02 PM",
        "आपका गैस कनेक्शन आज रात 8 बजे बंद कर दिया जाएगा क्योंकि आपकी KYC अधूरी है। तुरंत ₹1,520 इस UPI पर भेजें: "
        "gasseva.help@okaxis और मदद के लिए AnyDesk ऐप डाउनलोड करें।"),
     "truth": truth("any", "any", "any", scam_level=("warning",),
                    scam_signs=("threat_deadline", "personal_payment", "remote_app"))},
]
V1 = ("motor_renewal", "electricity_bill", "school_fee", "property_tax")


def main() -> None:
    gt_path = ROOT / "ground_truth.json"
    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    papers = {k: {**v, "scam_level": v.get("scam_level", ["none"]), "scam_signs": v.get("scam_signs", [])}
              for k, v in gt["papers"].items() if k in V1}
    for d in DOCS:
        (ROOT / "papers" / f"{d['id']}.html").write_text(d["html"], encoding="utf-8")
        papers[d["id"]] = d["truth"]
    gt["papers"] = papers
    gt_path.write_text(json.dumps(gt, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(DOCS)} documents; ground truth has {len(papers)} papers")


if __name__ == "__main__":
    main()
