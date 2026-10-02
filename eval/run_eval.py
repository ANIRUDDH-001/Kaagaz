"""Score any Gemma backend on the sample papers and spoken instructions.

  python -m eval.run_eval                                  # backend from .env
  $env:LLM_BACKEND="ollama"; python -m eval.run_eval       # local Gemma 4 E4B
Writes eval/results-<backend>.md."""
import asyncio
import json
import re
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
TRUTH = json.loads((ROOT / "ground_truth.json").read_text(encoding="utf-8"))
TODAY = date.fromisoformat(TRUTH["today"])


def score_paper(name: str, card: dict) -> dict[str, bool]:
    t = TRUTH["papers"][name]
    a = card["actions"][0]
    amount = a.get("amount_inr")
    consequence = (a.get("consequence") or "").lower()
    return {
        "category": a.get("category") == t["category"],
        "amount": amount is not None and abs(float(amount) - t["amount_inr"]) < 1,
        "due": a.get("due_date") == t["due_date"],
        "consequence": any(k in consequence for k in t["consequence_keywords"]),
        "hindi": bool(re.search(r"[ऀ-ॿ]{3,}", card.get("summary_hi") or "")),
    }


FLAG_KEYS = {"amount": "amount_inr", "due": "due_date"}


def silent_errors(s: dict[str, bool], action: dict) -> list[str]:
    """Wrong amount or date that the card did NOT highlight: the errors that could be saved unnoticed."""
    return [k for k, field in FLAG_KEYS.items() if not s[k] and field not in action.get("needs_check", [])]


def score_speech(name: str, card: dict) -> dict[str, bool]:
    expect = TRUTH["speech"][name]["expect"]
    got = card["actions"]
    result = {"tools": sorted(a["tool"] for a in got) == sorted(e["tool"] for e in expect)}
    for e in expect:
        match = next((a for a in got if a["tool"] == e["tool"]), {})
        for key, want in e.items():
            if key == "tool":
                continue
            have = match.get(key)
            if key == "amount_inr":
                result[f"{e['tool']}.{key}"] = have is not None and abs(float(have) - want) < 1
            else:
                result[f"{e['tool']}.{key}"] = have == want
    return result


async def _retry(make_call, tries: int = 4):
    for i in range(tries):
        try:
            t0 = time.time()
            return await make_call(), time.time() - t0
        except Exception as e:  # noqa: BLE001  the free tier is flaky; same retry idea as Temporal
            if i == tries - 1:
                raise
            print(f"   retry after {type(e).__name__}: {str(e)[:60]}")
            await asyncio.sleep(5 * (i + 1))


async def main() -> None:
    from ai.gemma import make_gemma
    from ai.understand import plan_speech, read_paper
    from app.config import get_settings

    settings = get_settings()
    gemma = make_gemma(settings)
    rows, fields_ok, fields_all, speech_ok, speech_all, flagged, silent = [], 0, 0, 0, 0, 0, 0
    for photo in sorted((ROOT / "photos").glob("*.jpg")):
        card, secs = await _retry(lambda p=photo: read_paper(gemma, p.read_bytes(), "image/jpeg", TODAY))
        s = score_paper(photo.stem, card)
        a = card["actions"][0]
        fields_ok += sum(s.values())
        fields_all += len(s)
        flagged += bool(a["needs_check"])
        silent += len(silent_errors(s, a))
        rows.append(f"| paper | {photo.stem} | {sum(s.values())}/{len(s)} | {secs:.1f}s | "
                    f"{', '.join(k for k, v in s.items() if not v) or '—'} | {', '.join(a['needs_check']) or '—'} |")
        print(rows[-1])
    for name, case in TRUTH["speech"].items():
        card, secs = await _retry(lambda c=case: plan_speech(gemma, c["said"], TRUTH["items"], TODAY, source="text"))
        s = score_speech(name, card)
        speech_ok += all(s.values())
        speech_all += 1
        rows.append(f"| speech | {name} | {sum(s.values())}/{len(s)} | {secs:.1f}s | "
                    f"{', '.join(k for k, v in s.items() if not v) or '—'} | — |")
        print(rows[-1])
    summary = (f"**{gemma.name}**: paper fields exactly right {fields_ok}/{fields_all}; "
               f"wrong amounts/dates NOT highlighted (silent errors) {silent}/8; "
               f"papers with a highlighted field {flagged}/4; spoken instructions fully right {speech_ok}/{speech_all}")
    out = ROOT / f"results-{settings.llm_backend}.md"
    out.write_text("\n".join([f"# Eval — {gemma.name} ({time.strftime('%Y-%m-%d %H:%M')})", "", summary, "",
                              "| kind | case | score | time | wrong | highlighted for checking |",
                              "|---|---|---|---|---|---|", *rows, ""]), encoding="utf-8")
    print(summary)
    print(f"wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
