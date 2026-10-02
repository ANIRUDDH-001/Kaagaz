"""Score a Gemma backend on the eval set:
- 26 fictitious papers and messages (6 scams), in 4 simulated photo conditions;
- 20 typed instructions;
- 8 synthetic-voice clips with background noise.

  python -m eval.run_eval                                   # everything, backend from .env
  python -m eval.run_eval --only papers --subset 6          # a quick look
  $env:LLM_BACKEND="ollama"; python -m eval.run_eval        # local Gemma 4 E4B
Writes eval/results-<backend>.md."""
import argparse
import asyncio
import json
import math
import re
import statistics
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
TRUTH = json.loads((ROOT / "ground_truth.json").read_text(encoding="utf-8"))
TODAY = date.fromisoformat(TRUTH["today"])
CONDITIONS = ("clean", "tilted", "dim", "creased")
FLAG_KEYS = {"amount": "amount_inr", "due": "due_date"}


def score_paper(truth: dict, card: dict) -> dict[str, bool]:
    a = card["actions"][0]
    s: dict[str, bool] = {}
    if truth["category"] != "any":
        allowed = truth["category"] if isinstance(truth["category"], list) else [truth["category"]]
        s["category"] = a.get("category") in allowed
    if truth["amount_inr"] != "any":
        want, have = truth["amount_inr"], a.get("amount_inr")
        s["amount"] = have is None if want is None else have is not None and abs(float(have) - want) < 1
    if truth["due_date"] != "any":
        s["due"] = a.get("due_date") == truth["due_date"]
    if truth.get("consequence_keywords"):
        consequence = (a.get("consequence") or "").lower()
        s["consequence"] = any(k.lower() in consequence for k in truth["consequence_keywords"])
    s["hindi"] = bool(re.search(r"[ऀ-ॿ]{3,}", card.get("summary_hi") or ""))
    return s


def silent_errors(s: dict[str, bool], action: dict) -> list[str]:
    """A wrong amount or date that the card did NOT highlight: the errors that could be saved unnoticed."""
    return [k for k, field in FLAG_KEYS.items() if k in s and not s[k] and field not in action.get("needs_check", [])]


def score_scam(truth: dict, card: dict) -> dict:
    scam = card.get("scam") or {"level": "none", "signs": []}
    found = {x["sign"] for x in scam["signs"]}
    return {"level_ok": scam["level"] in truth["scam_level"],
            "false_alarm": scam["level"] == "warning" and "warning" not in truth["scam_level"],
            "signs_found": len(found & set(truth["scam_signs"])), "signs_expected": len(truth["scam_signs"])}


def score_speech(expect: list[dict], card: dict) -> dict[str, bool]:
    got = card["actions"]
    result = {"tools": sorted(a["tool"] for a in got) == sorted(e["tool"] for e in expect)}
    for e in expect:
        match = next((a for a in got if a["tool"] == e["tool"] and
                      (not e.get("obligation_id") or a.get("obligation_id") == e["obligation_id"])),
                     next((a for a in got if a["tool"] == e["tool"]), {}))
        for key, want in e.items():
            if key == "tool":
                continue
            have = match.get(key)
            if key == "amount_inr":
                result[f"{e['tool']}.{key}"] = have is not None and abs(float(have) - want) < 1
            else:
                result[f"{e['tool']}.{key}"] = have == want
    return result


def latency(secs: list[float]) -> tuple[float, float]:
    xs = sorted(secs)
    return statistics.median(xs), xs[max(0, math.ceil(0.9 * len(xs)) - 1)]


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

    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="papers,speech,audio")
    ap.add_argument("--subset", type=int, default=0, help="first N documents / cases only")
    args = ap.parse_args()
    only = set(args.only.split(","))
    settings = get_settings()
    gemma = make_gemma(settings)
    out: list[str] = []
    secs_all: list[float] = []
    summary: list[str] = []

    if "papers" in only:
        docs = list(TRUTH["papers"].items())[: args.subset or None]
        by_cond = defaultdict(lambda: [0, 0, 0])            # right, scored, silent
        scam_rows, false_alarms, caught, scam_total, rows = [], [], 0, 0, []
        for name, truth in docs:
            for cond in CONDITIONS:
                photo = ROOT / "photos" / f"{name}__{cond}.jpg"
                card, secs = await _retry(lambda p=photo: read_paper(gemma, p.read_bytes(), "image/jpeg", TODAY))
                secs_all.append(secs)
                s, sc, a = score_paper(truth, card), score_scam(truth, card), card["actions"][0]
                silent = silent_errors(s, a)
                c = by_cond[cond]
                c[0] += sum(s.values())
                c[1] += len(s)
                c[2] += len(silent)
                if sc["false_alarm"]:
                    false_alarms.append(f"{name} ({cond})")
                if truth["scam_level"] == ["warning"]:
                    scam_total += 1
                    caught += sc["level_ok"]
                level = (card.get("scam") or {}).get("level", "none")
                rows.append(f"| {name} | {cond} | {sum(s.values())}/{len(s)} | {secs:.1f}s | "
                            f"{', '.join(k for k, v in s.items() if not v) or '—'} | "
                            f"{', '.join(a.get('needs_check', [])) or '—'} | {level} |")
                print(rows[-1])
        right = sum(c[0] for c in by_cond.values())
        scored = sum(c[1] for c in by_cond.values())
        silent_total = sum(c[2] for c in by_cond.values())
        summary += [f"- Paper fields exactly right: **{right}/{scored}** ({100 * right / max(scored, 1):.0f}%)",
                    f"- Wrong amounts or dates that were NOT highlighted (silent errors): **{silent_total}**",
                    f"- Scam messages shown the red warning: **{caught}/{scam_total}**",
                    f"- Genuine papers wrongly shown the red warning (false alarms): **{len(false_alarms)}**"
                    + (f" — {', '.join(false_alarms)}" if false_alarms else "")]
        out += ["## Papers by photo condition (simulated)", "", "| condition | fields right | silent errors |",
                "|---|---|---|"]
        out += [f"| {cond} | {by_cond[cond][0]}/{by_cond[cond][1]} | {by_cond[cond][2]} |" for cond in CONDITIONS]
        out += ["", "## Every photo", "", "| document | condition | score | time | wrong | highlighted | scam level |",
                "|---|---|---|---|---|---|---|", *rows, ""]

    for kind in ("speech", "audio"):
        if kind not in only:
            continue
        cases = list(TRUTH[kind].items())[: args.subset or None]
        stt = None
        if kind == "audio":
            from ai.stt import make_stt
            stt = make_stt(settings)
        ok, rows = 0, []
        for name, case in cases:
            expect = TRUTH["speech"][case["case"]]["expect"] if kind == "audio" else case["expect"]

            async def run(case=case):
                said = case["said"] if kind == "speech" else await stt.transcribe(str(ROOT / "audio" / f"{name}.wav"),
                                                                                  "audio/wav")
                return await plan_speech(gemma, said, TRUTH["items"], TODAY, source="text"), said
            (card, said), secs = await _retry(run)
            secs_all.append(secs)
            s = score_speech(expect, card)
            ok += all(s.values())
            heard = f" — heard: {said}" if kind == "audio" else ""
            rows.append(f"| {name} | {sum(s.values())}/{len(s)} | {secs:.1f}s | "
                        f"{', '.join(k for k, v in s.items() if not v) or '—'}{heard} |")
            print(rows[-1])
        label = "Typed instructions" if kind == "speech" else "Spoken clips (synthetic voice + noise)"
        summary.append(f"- {label} fully right: **{ok}/{len(cases)}**")
        out += [f"## {label}", "", "| case | score | time | wrong |", "|---|---|---|---|", *rows, ""]

    if secs_all:
        med, p90 = latency(secs_all)
        summary.append(f"- Time per call: median **{med:.1f} s**, 90th percentile **{p90:.1f} s**")
    path = ROOT / f"results-{settings.llm_backend}.md"
    head = [f"# Eval — {gemma.name} ({time.strftime('%Y-%m-%d %H:%M')})", "",
            "Fictitious documents; photo conditions and voices are simulated (see eval/README).", "", *summary, ""]
    path.write_text("\n".join(head + out), encoding="utf-8")
    print("\n".join(summary))
    print(f"wrote {path}")


if __name__ == "__main__":
    asyncio.run(main())
