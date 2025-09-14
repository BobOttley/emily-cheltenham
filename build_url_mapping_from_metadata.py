#!/usr/bin/env python3
"""
Builds url_mapping.py from scraper output (metadata.pkl or kb_chunks/kb_chunks.pkl).

Goals:
- Prefer on-site pages (e.g. *.cheltenhamcollege.org) over S3/CDN when possible.
- Prefer HTML pages for general topics; prefer PDFs only for policy topics.
- Exclude Prep URLs if requested.
- Robust topic detection via title, path and filename heuristics.
- Output a clean, small mapping that downstream code can rely on.

Usage (Cheltenham example):
  python build_url_mapping_from_metadata.py \
    --in metadata.pkl \
    --out url_mapping.py \
    --prefer-domain cheltenhamcollege.org \
    --site-root https://www.cheltenhamcollege.org/ \
    --exclude-prep
"""

import os, re, sys, argparse, pickle, json
import urllib.parse as up
from collections import defaultdict

# -------- Helpers --------



def normalise_url(u: str) -> str:
    u = u.strip()
    if not u:
        return u
    # drop fragments + query
    parts = up.urlsplit(u)
    parts = parts._replace(query="", fragment="")
    return up.urlunsplit(parts)

def is_pdf(u: str) -> bool:
    return up.urlsplit(u).path.lower().endswith(".pdf")

def domain(u: str) -> str:
    return up.urlsplit(u).netloc.lower()

def shortness(u: str) -> int:
    """Heuristic: shorter path is 'cleaner'."""
    return len(up.urlsplit(u).path)

def contains_any(s: str, words) -> bool:
    s2 = s.lower()
    return any(w in s2 for w in words)

def prefer_on_site(urls, prefer_domain: str):
    """Keep only URLs on prefer_domain if any exist; otherwise keep all."""
    on = [u for u in urls if domain(u).endswith(prefer_domain)]
    return on if on else urls

def drop_prep(urls):
    res = []
    for u in urls:
        p = up.urlsplit(u).path.lower()
        if "/prep" in p or "pre-prep" in p or "/the-prep" in p or "/prep-school" in p:
            continue
        res.append(u)
    return res

# -------- Topic catalogue (labels → rules) --------
# Each entry defines:
#   - 'match': list of regex/keywords to score
#   - 'prefer_pdf': True/False  (policies prefer PDFs)
#   - 'aliases': optional extra labels to consider in generator later
TOPICS = {
    "Admissions": {"match": ["admission", "apply", "registration", "join(ing)?"], "prefer_pdf": False},
    "Enquiry": {"match": ["enquir", "contact admissions", "get in touch", "request information|request info|contact us|contact"], "prefer_pdf": False},
    "Open Events": {"match": ["open (day|morning|evening|event)", r"\bvisit\b", r"\btour\b"], "prefer_pdf": False},
    "Fees": {"match": ["fee", "tuition", "charges", "cost"], "prefer_pdf": False},
    "Scholarships and Bursaries": {"match": ["scholarship", "bursar", "financial aid", "award"], "prefer_pdf": False},
    "Term Dates": {"match": ["term date", "calendar", "holiday dates", "half term"], "prefer_pdf": False},
    "Sixth Form": {"match": ["sixth form", r"\ba-?level"], "prefer_pdf": False},
    "Subjects": {"match": ["subject", "curriculum", "academic overview|departments|courses"], "prefer_pdf": False},
    "Boarding": {"match": ["boarding", "boarding principles", "houses"], "prefer_pdf": False},
    "Learning Support": {"match": ["send", r"\bsen\b", "learning support", "academic support", "eal"], "prefer_pdf": False},
    "Pastoral Care": {"match": ["pastoral", "wellbeing", "welfare"], "prefer_pdf": False},

    # Policies – prefer direct PDFs
    "Safeguarding Policy": {"match": ["safeguarding", "child protection"], "prefer_pdf": True},
    "Behaviour Policy": {"match": ["behaviour", "discipline", "code of conduct"], "prefer_pdf": True},
    "Anti-Bullying Policy": {"match": ["anti-?bully"], "prefer_pdf": True},
    "Complaints Policy": {"match": ["complaint"], "prefer_pdf": True},
    "ISI Report": {"match": ["isi inspection|inspection report", r"\bisi\b"], "prefer_pdf": True},
    "Privacy Policy": {"match": ["privacy"], "prefer_pdf": False},  # often HTML
    "Cookies": {"match": ["cookie policy|cookies"], "prefer_pdf": False},

    # Co-curricular & extras
    "Co-curricular": {"match": ["co-?curricular", "clubs", "societies", "activities"], "prefer_pdf": False},
    "Sport": {"match": [r"\bsport(s)?\b", r"\bpe\b", "fixtures"], "prefer_pdf": False},
    "Music": {"match": [r"\bmusic\b", "choir", "orchestra"], "prefer_pdf": False},
    "Destinations": {"match": ["destination", "leavers", "university"], "prefer_pdf": False},
    "Results": {"match": ["result", "gcse", "a-?level", "examination"], "prefer_pdf": False},
    "Uniform": {"match": ["uniform", "outfitters"], "prefer_pdf": False},
    "Transport": {"match": ["transport", "bus", "coach", "minibus"], "prefer_pdf": False},
    "Governors": {"match": ["governors", "board of governors", "trustees"], "prefer_pdf": False},
    "Staff": {"match": ["staff list", "staff directory", "meet the staff"], "prefer_pdf": False},
    "Policies": {"match": ["policies"], "prefer_pdf": False},
    "Contact": {"match": ["contact", "how to find us"], "prefer_pdf": False},
    "Homepage": {"match": ["home"], "prefer_pdf": False},
}

POLICY_LABELS = {k for k, v in TOPICS.items() if v.get("prefer_pdf")}
GENERAL_LABELS = set(TOPICS.keys()) - POLICY_LABELS

def score_topic(label: str, title: str, path: str, is_pdf_flag: bool) -> float:
    """Simple keyword score; more keywords matched → higher score; bonus if PDF for policy labels."""
    rules = TOPICS[label]["match"]
    s = (title + " " + path).lower()
    score = 0.0
    for pat in rules:
        if re.search(pat, s, flags=re.I):
            score += 1.0
    # Encourage PDF for policy labels
    if label in POLICY_LABELS and is_pdf_flag:
        score += 0.75
    # Slight bonus for exact keyword in filename
    fname = os.path.basename(path.lower())
    if any(re.search(p, fname, flags=re.I) for p in rules):
        score += 0.5
    return score

def choose_best(candidates, prefer_domain: str, prefer_pdf: bool):
    """
    candidates: list of urls
    1) prefer on-site domain
    2) if prefer_pdf, prefer PDFs; else prefer HTML
    3) then choose shortest path
    """
    if not candidates:
        return None
    C = prefer_on_site(candidates, prefer_domain)

    if prefer_pdf:
        pdfs = [u for u in C if is_pdf(u)]
        C = pdfs if pdfs else C
    else:
        htmls = [u for u in C if not is_pdf(u)]
        C = htmls if htmls else C

    C = sorted(set(C), key=lambda u: (shortness(u), u))
    return C[0] if C else None

def build_mapping(records, prefer_domain: str, site_root: str, exclude_prep: bool):
    # Prepare candidate pools per label
    pools = defaultdict(list)
    for rec in records:
        u = normalise_url(rec["url"])
        if not u:
            continue
        if exclude_prep and ("/prep" in u.lower() or "pre-prep" in u.lower() or "/the-prep" in u.lower()):
            continue

        t = (rec.get("title") or "").strip()
        path = up.urlsplit(u).path
        pdf_flag = is_pdf(u)

        # Try all labels, accumulate if non-zero score
        for label in TOPICS.keys():
            sc = score_topic(label, t, path, pdf_flag)
            if sc > 0:
                pools[label].append((u, sc))

    mapping = {}

    # Always ensure homepage + contact exist
    homepage_candidates = [r["url"] for r in records if domain(r["url"]).endswith(prefer_domain)]
    mapping["Homepage"] = site_root.rstrip("/") + "/"
    contact_pool = [u for u, _ in pools.get("Contact", [])]
    mapping["Contact"] = choose_best(contact_pool, prefer_domain, prefer_pdf=False) or site_root.rstrip("/") + "/contact-us/"

    # For each topic, pick best
    for label, pool in pools.items():
        urls_sorted = [u for (u, _) in sorted(pool, key=lambda x: x[1], reverse=True)]
        best = choose_best(urls_sorted, prefer_domain, prefer_pdf=TOPICS[label]["prefer_pdf"])
        if best:
            mapping[label] = best

    # Fallback tidy-ups: if missing some key anchors, provide sane defaults on-site
    defaults = {
        "Admissions": site_root.rstrip("/") + "/admissions/",
        "Fees": site_root.rstrip("/") + "/admissions/fees/",
        "Open Events": site_root.rstrip("/") + "/events/open-morning/",
        "Scholarships and Bursaries": site_root.rstrip("/") + "/scholarships-key-dates/",
        "Term Dates": site_root.rstrip("/") + "/key-information-for-parents/term-dates/",
        "Sixth Form": site_root.rstrip("/") + "/college/sixth-form/",
        "Subjects": site_root.rstrip("/") + "/college/academic-overview/",
        "Boarding": site_root.rstrip("/") + "/college/health-wellbeing/boarding-pastoral-care/",
        "Learning Support": site_root.rstrip("/") + "/admissions/learning-support-eal/",
        "Co-curricular": site_root.rstrip("/") + "/college/co-curricular/",
        "Sport": site_root.rstrip("/") + "/college/sport/",
    }
    for k, v in defaults.items():
        if k not in mapping:
            mapping[k] = v

    return mapping

def write_mapping(mapping: dict, out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Auto-generated from metadata.pkl – do not edit by hand.\n")
        f.write("URL_MAPPING = {\n")
        for k in sorted(mapping.keys()):
            f.write(f'  "{k}": "{mapping[k]}",\n')
        f.write("}\n")
    print(f"✅ Wrote {out_path} with {len(mapping)} entries.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input_path", required=False, default="metadata.pkl", help="Path to metadata.pkl or kb_chunks/kb_chunks.pkl")
    ap.add_argument("--out", dest="out_path", required=False, default="url_mapping.py")
    ap.add_argument("--prefer-domain", dest="prefer_domain", required=True, help="Primary site domain (e.g. cheltenhamcollege.org)")
    ap.add_argument("--site-root", dest="site_root", required=True, help="Site root URL (e.g. https://www.cheltenhamcollege.org/)")
    ap.add_argument("--exclude-prep", dest="exclude_prep", action="store_true", help="Exclude prep/pre-prep pages")
    args = ap.parse_args()

    records = load_metadata(args.input_path)
    mapping = build_mapping(records, args.prefer_domain, args.site_root, args.exclude_prep)
    write_mapping(mapping, args.out_path)

if __name__ == "__main__":
    main()
