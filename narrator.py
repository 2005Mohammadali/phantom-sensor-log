import requests
from config import OLLAMA_URL, MODEL

STYLE = ("You are a ghost haunting a computer. Write a spooky micro-fiction of 3 or 4 sentences, "
         "atmospheric, with Halloween or Dia de los Muertos imagery (candles, marigolds, "
         "restless spirits). Use ONLY the facts given and never invent numbers. "
         "No lists, no headings, no preamble.")

def _ask(prompt, tokens=170):
    r = requests.post(OLLAMA_URL, json={
        "model": MODEL, "prompt": prompt, "stream": False,
        "options": {"temperature": 0.9, "num_predict": tokens}}, timeout=300)
    return r.json()["response"].strip()

def tell(facts, tier):
    try:
        return _ask(f"{STYLE}\nSeverity: {tier}\nFacts: {facts}\nTale:")
    except Exception:
        return f"[{tier}] The ghost's voice is silent (is Ollama running?). Facts: {facts}"

def epitaph(name, lifespan_s, rss_mb):
    try:
        return _ask(f"Write a one-sentence tender, spooky epitaph for a computer process named "
                    f"'{name}' that lived {lifespan_s/60:.1f} minutes and used {rss_mb:.0f} MB "
                    f"of memory. Dia de los Muertos tone. One sentence only.", 60)
    except Exception:
        return "It rests now, among the marigolds."

def dawn(counts, facts_list):
    try:
        return _ask(f"{STYLE}\nSummarize the night's hauntings as a dawn report. "
                    f"Counts by severity: {counts}. Sample events: {facts_list}\nTale:", 200)
    except Exception:
        return f"Dawn breaks. Hauntings: {counts}."