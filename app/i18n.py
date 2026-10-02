"""Every fixed message the server can show, in English and Hindi. The client shows the one for its language."""

MESSAGES: dict[str, tuple[str, str]] = {
    # errors
    "gone": ("This photo or recording is no longer on the server. Please send it again.",
             "यह काग़ज़ या आवाज़ अब सर्वर पर नहीं है — कृपया फिर से भेजिए।"),
    "bad_input": ("Couldn't understand that. Please try again with a clearer photo or recording.",
                  "समझ नहीं आया — कृपया साफ़ फ़ोटो या आवाज़ के साथ फिर से कोशिश करें।"),
    "empty": ("I didn't hear anything. Please speak again.", "कोई आवाज़ सुनाई नहीं दी — फिर से बोलिए।"),
    "busy": ("The AI is busy right now. Please try again in a little while.",
             "AI अभी व्यस्त है — थोड़ी देर में फिर कोशिश करें।"),
    "ai_limit": ("This hour's AI limit is used up. Please try again a little later.",
                 "इस घंटे की AI सीमा पूरी हो गई — थोड़ी देर बाद कोशिश करें।"),
    "tts_limit": ("This hour's voice limit is used up. Your phone's own voice will read instead.",
                  "इस घंटे की आवाज़ सीमा पूरी हो गई — फ़ोन की अपनी आवाज़ में सुनाऊँगा।"),
    "too_many_households": ("Too many new households from here. Please come back a little later.",
                            "बहुत सारे नए खाते बन गए — थोड़ी देर बाद आइए।"),
    "file_too_big": ("The file is too big (over 8 MB). Please send a smaller photo.",
                     "फ़ाइल बहुत बड़ी है (8 MB से ज़्यादा) — छोटी फ़ोटो भेजिए।"),
    "not_found": ("That paper wasn't found.", "वह काग़ज़ नहीं मिला।"),
    "saving": ("Already saving.", "पहले से सेव हो रहा है।"),
    "not_ready": ("Not ready yet.", "अभी तैयार नहीं है।"),
    "card_changed": ("This card has changed. Please send it again.", "यह कार्ड बदल गया है — कृपया फिर से भेजिए।"),
    "date_required": ("A due date is needed. Please fill in the date.", "आख़िरी तारीख़ ज़रूरी है — कृपया तारीख़ भरिए।"),
    "date_unclear": ("Couldn't understand the date.", "तारीख़ समझ नहीं आई।"),
    "date_past": ("Can't remind on a date that has passed. Please pick a later date.",
                  "बीती हुई तारीख़ पर याद नहीं दिला सकते — आगे की तारीख़ चुनिए।"),
    "date_wrong": ("That date doesn't look right.", "यह तारीख़ सही नहीं लग रही।"),
    "amount_wrong": ("That amount doesn't look right.", "रकम सही नहीं लग रही।"),
    "nothing_changed": ("Nothing changed.", "कुछ बदला नहीं।"),
    "already_done": ("This is already done.", "यह काम पहले ही पूरा हो चुका है।"),
    "reminders_closed": ("Reminders for this have ended. Show the paper again to add it fresh.",
                         "इसके reminder बंद हो चुके हैं — काग़ज़ फिर से दिखाकर नया जोड़िए।"),
    "try_later": ("Couldn't save right now. Please try again in a little while.",
                  "अभी सेव नहीं हो पाया — थोड़ी देर में फिर कोशिश कीजिए।"),
    "no_warning": ("There's no warning on this card to send.", "इस कार्ड पर कोई चेतावनी नहीं है।"),
    "not_done_yet": ("Mark it done first.", "पहले इसे 'हो गया' कीजिए।"),
    "not_yearly": ("This kind of paper doesn't come every year.", "यह काग़ज़ हर साल नहीं आता।"),
    # questions the app asks
    "which_paper": ("Which paper do you mean? Please say its name.", "कौन से काग़ज़ की बात है? उसका नाम बताइए।"),
    "which_date": ("Which date should I remind you again?", "किस तारीख़ को फिर याद दिलाऊँ?"),
    "what_change": ("What should change — the amount or the date?", "क्या बदलना है — रकम या तारीख़?"),
    "not_understood": ("Sorry, I didn't understand. Please say it again.", "माफ़ कीजिए, समझ नहीं पाया। फिर से बोलिए।"),
}


def msg(code: str) -> dict[str, str]:
    en, hi = MESSAGES[code]
    return {"code": code, "en": en, "hi": hi}
