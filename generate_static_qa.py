#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGGRESSIVE static QA generator:
- Uses url_mapping.py for core anchors (fees, admissions, safeguarding, etc.)
- Scans metadata.pkl to AUTO-ADD:
  * All 'policy-like' items (prefers PDFs, falls back to HTML)
  * All sport pages (per a configurable sports catalogue)

Outputs a ready-to-use static_qa_config.py with British English copy.

Usage (Cheltenham example):
  python generate_static_qa.py \
    --mapping url_mapping.py \
    --metadata metadata.pkl \
    --out static_qa_config.py \
    --school "Cheltenham College" \
    --site-root "https://www.cheltenhamcollege.org/" \
    --exclude-prep
"""

import os, re, argparse, pickle, importlib.util, textwrap
from collections import defaultdict
from typing import Dict, List, Tuple

# -----------------------
# Configurable Catalogues
# -----------------------

SPORT_KEYWORDS = {
    # sport_key: [keyword variants]
    "rugby": ["rugby"],
    "hockey": ["hockey"],
    "cricket": ["cricket"],
    "tennis": ["tennis"],
    "rowing": ["rowing", "boat club"],
    "football": ["football", "soccer"],
    "netball": ["netball"],
    "swimming": ["swimming", "swim"],
    "athletics": ["athletics", "track and field", "track & field"],
    "cross country": ["cross country", "xc"],
    "basketball": ["basketball"],
    "golf": ["golf"],
    "squash": ["squash"],
    "badminton": ["badminton"],
    "table tennis": ["table tennis", "ping pong"],
    "fencing": ["fencing"],
    "climbing": ["climbing"],
    "equestrian": ["equestrian"],
    "gymnastics": ["gymnastics"],
    "dance": ["dance"],
    "lacrosse": ["lacrosse"],
    "water polo": ["water polo"],
}

# If any of these substrings appear in title/path/filename → treat as policy-like.
POLICY_HINTS = [
    "policy", "policies", "procedure", "procedures", "statement",
    "guidance", "charter", "code", "regulation", "regulations",
    "protocol", "privacy", "cookies", "complaints", "safeguard",
    "anti-bully", "bullying", "behaviour", "behavior", "discipline",
    "first aid", "medical", "health and safety", "h&s",
    "whistleblow", "charging and remissions", "data protection",
    "gdpr", "equalit", "inclusion", "esafety", "e-safety", "acceptable use",
    "aup", "alcohol", "drugs", "attendance", "exclusion", "send", "sen", "eal",
    "remote learning", "homework", "assessment", "complaints procedure",
    "anti-bullying", "safeguarding policy", "child protection",
    "accessibility", "access arrangements"
]

# Heuristics to exclude unwanted areas (tweakable)
EXCLUDE_PATH_HINTS = [
    "/the-prep", "/prep", "pre-prep", "/nursery", "/early-years"
]

# -----------------------
# Utility helpers
# -----------------------

def import_url_mapping(mapping_path: str) -> Dict[str, str]:
    spec = importlib.util.spec_from_file_location("url_mapping", mapping_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Failed to import {mapping_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "URL_MAPPING", {})

def load_metadata(pkl_path: str) -> List[dict]:
    with open(pkl_path, "rb") as f:
        data = pickle.load(f)

    if isinstance(data, dict):
        recs = list(data.values())
    elif isinstance(data, list):
        recs = data
    else:
        raise ValueError("Unsupported metadata format; expected list or dict")

    norm = []
    for r in recs:
        url = r.get("url") or r.get("source_url") or r.get("page_url")
        title = (r.get("title") or r.get("page_title") or r.get("label") or "").strip()
        text = (r.get("text") or "").strip()
        if url:
            norm.append({"url": url.strip(), "title": title, "text": text})
    return norm

def is_pdf(url: str) -> bool:
    return url.lower().split("?")[0].endswith(".pdf")

def normalise_url(u: str) -> str:
    # Strip fragment & query for canonicalisation
    from urllib.parse import urlsplit, urlunsplit
    p = urlsplit(u)
    p = p._replace(query="", fragment="")
    return urlunsplit(p)

def contains_any(s: str, needles: List[str]) -> bool:
    s2 = s.lower()
    return any(n in s2 for n in needles)

def looks_like_policy(title: str, path: str, filename: str) -> bool:
    hay = " ".join([title.lower(), path.lower(), filename.lower()])
    return contains_any(hay, POLICY_HINTS)

def pick(mapping: Dict[str, str], candidates: List[str], default: str) -> str:
    if not mapping:
        return default
    lower_map = {k.lower(): v for k, v in mapping.items()}
    for c in candidates:
        u = lower_map.get(c.lower())
        if u:
            if any(h in u.lower() for h in EXCLUDE_PATH_HINTS):
                continue
            return u
    return default

def L(page_links: Dict[str, str], key: str, site_root: str) -> str:
    return page_links.get(key, site_root)

def dedupe_preserve_order(items: List[Tuple[str, dict]]) -> List[Tuple[str, dict]]:
    seen = set()
    out = []
    for k, v in items:
        sig = (k.lower(), v.get("url"))
        if sig in seen: 
            continue
        seen.add(sig)
        out.append((k, v))
    return out

# -----------------------
# Core anchors (curated)
# -----------------------

def core_page_links(url_mapping: Dict[str, str], site_root: str, school: str) -> Dict[str, str]:
    def _pick(keys, default):
        return pick(url_mapping, keys, default)

    links = {
        "admissions": _pick(["Admissions", "Join Us", "Admissions (College)", f"Joining {school}"], site_root),
        "enquiry": _pick(["Enquiry", "Enquire", "Enquiry Form", "Contact Admissions", "Contact"], site_root),
        "open events": _pick(["Open Events", "Open Mornings", "Open Day", "Visit Us"], site_root),
        "fees": _pick(["Fees", "Tuition Fees", "College Fees"], site_root),
        "scholarships": _pick(["Scholarships and Bursaries", "Scholarships", "Bursaries"], site_root),
        "term dates": _pick(["Term Dates", "Calendar"], site_root),
        "calendar": _pick(["Calendar", "Term Dates"], site_root),
        "sixth form": _pick(["Sixth Form"], site_root),
        "subjects": _pick(["Subjects", "Curriculum", "Academic", "Departments"], site_root),
        "pastoral": _pick(["Pastoral Care", "Wellbeing"], site_root),
        "boarding": _pick(["Boarding", "Boarding Principles"], site_root),
        "safeguarding": _pick(["Safeguarding Policy", "Safeguarding"], site_root),
        "send": _pick(["Learning Support", "SEND", "SEN", "Academic Support", "EAL"], site_root),
        "behaviour policy": _pick(["Behaviour Policy"], site_root),
        "anti-bullying": _pick(["Anti-Bullying Policy", "Bullying"], site_root),
        "complaints": _pick(["Complaints Policy", "Complaints Procedure"], site_root),
        "isi report": _pick(["ISI Report", "Inspection Report"], site_root),
        "co-curricular": _pick(["Co-curricular", "Clubs & Societies", "Activities"], site_root),
        "sport": _pick(["Sport", "Games", "PE"], site_root),
        "music": _pick(["Music"], site_root),
        "results": _pick(["Results", "Exam Results", "Academic Results"], site_root),
        "destinations": _pick(["Destinations", "Leavers' Destinations", "University Destinations"], site_root),
        "uniform": _pick(["Uniform"], site_root),
        "transport": _pick(["Transport", "Bus Routes", "Coach"], site_root),
        "governors": _pick(["Governors", "Board of Governors", "Trustees"], site_root),
        "staff": _pick(["Staff", "Staff List", "Directory"], site_root),
        "policies": _pick(["Policies"], site_root),
        "privacy": _pick(["Privacy Policy"], site_root),
        "cookies": _pick(["Cookies", "Cookie Policy"], site_root),
        "contact": _pick(["Contact", "Contact Us", "How to Find Us"], site_root),
        "home": site_root,
        "homepage": site_root,
        "main page": site_root,
    }
    return links

def core_static_items(school: str) -> List[Tuple[str, dict]]:
    # “Curated” base set (kept intentionally lean and guaranteed)
    items = [
        ("admissions", {"answer": f"{school} admissions information, entry process and who to contact.", "label": "Admissions", "variants": ["admissions","apply","join","application","registration","how to apply","entry process"]}),
        ("enquiry", {"answer": "Send an enquiry to our Admissions team and we’ll be in touch with next steps.", "label": "Send an enquiry", "variants": ["enquiry","enquire","contact admissions","ask a question","request information"]}),
        ("open events", {"answer": "We host open mornings and visit opportunities throughout the year. Choose a date and register online.", "label": "Open events", "variants": ["open morning","open day","visit","tour","open evening"]}),
        ("fees", {"answer": "Current fees (including boarding and day) are listed on our fees page.", "label": "View fees", "variants": ["fees","tuition","charges","costs","price"]}),
        ("scholarships", {"answer": "We offer a range of scholarships and bursaries. Guidance and criteria are available online.", "label": "Scholarships & bursaries", "variants": ["scholarships","bursaries","financial aid","awards"]}),
        ("term dates", {"answer": "Term dates and the school calendar are available online.", "label": "Term dates", "variants": ["term dates","calendar","half term","holiday dates"]}),
        ("sixth form", {"answer": "Explore Sixth Form life, subjects and opportunities.", "label": "Sixth Form", "variants": ["sixth form","a level","a-level"]}),
        ("subjects", {"answer": "Find details of subjects and the academic programme.", "label": "Subjects & curriculum", "variants": ["subjects","curriculum","departments","academic"]}),
        ("pastoral", {"answer": "Pastoral care and wellbeing information.", "label": "Pastoral care", "variants": ["pastoral","wellbeing","support"]}),
        ("boarding", {"answer": f"{school} offers boarding and day places. Read about our boarding information and principles.", "label": "Boarding", "variants": ["boarding","houses","boarder","boarding principles"]}),
        ("safeguarding", {"answer": "Read about safeguarding and our policies.", "label": "Safeguarding", "variants": ["safeguarding","child protection"]}),
        ("send", {"answer": "Information about learning support (SEND).", "label": "Learning support (SEND)", "variants": ["send","sen","learning support","academic support","eal"]}),
        ("behaviour policy", {"answer": "Read the behaviour policy.", "label": "Behaviour policy", "variants": ["behaviour","discipline","code of conduct"]}),
        ("anti-bullying", {"answer": "Read the anti-bullying policy.", "label": "Anti-bullying policy", "variants": ["anti bullying","bullying"]}),
        ("complaints", {"answer": "Read the complaints policy and procedure.", "label": "Complaints policy", "variants": ["complaints","complaint procedure"]}),
        ("isi report", {"answer": "Read the latest inspection (ISI) report.", "label": "ISI report", "variants": ["isi","inspection report","isi inspection"]}),
        ("co-curricular", {"answer": "Co-curricular opportunities, clubs and activities.", "label": "Co-curricular", "variants": ["co-curricular","clubs","activities","societies"]}),
        ("sport", {"answer": "Sport at school, including fixtures and programmes.", "label": "Sport", "variants": ["sport","games","pe","fixtures"]}),
        ("music", {"answer": "Music opportunities and ensembles.", "label": "Music", "variants": ["music","choir","orchestra"]}),
        ("results", {"answer": "Recent academic results and headline outcomes.", "label": "Results", "variants": ["results","exam results","academic results","grades"]}),
        ("destinations", {"answer": "Leavers’ destinations and university entries.", "label": "Leavers’ destinations", "variants": ["destinations","university destinations","leavers"]}),
        ("uniform", {"answer": "Uniform information and outfitters.", "label": "Uniform", "variants": ["uniform","outfitters"]}),
        ("transport", {"answer": "Transport routes and travel information.", "label": "Transport", "variants": ["transport","bus","coach","minibus"]}),
        ("governors", {"answer": "Meet the Governors / Trustees.", "label": "Governors", "variants": ["governors","board of governors","trustees"]}),
        ("staff", {"answer": "Find staff information and contacts.", "label": "Staff", "variants": ["staff","staff list","directory","teachers"]}),
        ("policies", {"answer": "Browse all policies.", "label": "Policies", "variants": ["policies","policy list"]}),
        ("privacy", {"answer": "Read our Privacy Policy.", "label": "Privacy Policy", "variants": ["privacy","gdpr","data protection"]}),
        ("cookies", {"answer": "Cookie Policy.", "label": "Cookies", "variants": ["cookies","cookie policy"]}),
        ("contact", {"answer": "Get in touch with the school team.", "label": "Contact", "variants": ["contact","contact us","how to find us","phone number","email"]}),
    ]
    return items

# -----------------------
# AUTO: discover policies
# -----------------------

def discover_policies(records: List[dict], exclude_prep: bool, prefer_domain: str = "") -> Dict[str, str]:
    """
    Return {policy_label: url}. Prefers PDFs; falls back to HTML if needed.
    Policy label is prettified from title/filename, e.g., "First Aid Policy".
    """
    candidates = defaultdict(list)  # key → list[(url, score, is_pdf)]
    for r in records:
        url = normalise_url(r["url"])
        title = r["title"] or ""
        path = url
        if exclude_prep and any(h in url.lower() for h in EXCLUDE_PATH_HINTS):
            continue

        # Only consider pages that *look* like policies or PDFs that are clearly policies
        fname = os.path.basename(url.lower())
        pdf = is_pdf(url)
        if not (pdf or looks_like_policy(title, path, fname)):
            continue

        # Build a display label
        label = title.strip()
        if not label:
            # derive from filename
            label = os.path.splitext(os.path.basename(url))[0]
            label = label.replace("_", " ").replace("-", " ").strip()

        # normalise label to title case, ensure 'Policy' suffix where appropriate
        base = re.sub(r"\s*\b(pdf|docx?)\b\s*$", "", label, flags=re.I).strip()
        # If it already contains 'policy', leave; else add if it looks like a policy-ish doc
        if not re.search(r"\bpolicy\b", base, flags=re.I) and looks_like_policy(base, path, fname):
            # don't force 'Policy' onto reports like ISI; just leave as-is if 'report' present
            if not re.search(r"\breport\b", base, flags=re.I):
                base = base + " Policy"

        # Clean multiple spaces, title-case lightly (preserve common acronyms)
        base = re.sub(r"\s{2,}", " ", base)
        # Capitalise first letter of words except minor ones
        base = " ".join(w.capitalize() if w.lower() not in {"and","of","for","to","in","on","with"} else w.lower() for w in base.split())

        # Score: favour PDFs and shorter URLs
        score = (2.0 if pdf else 0.0) + max(0, 120 - len(url))
        # Prefer on-site domain
        if prefer_domain and prefer_domain in url.lower():
            score += 1.0

        candidates[base].append((url, score, pdf))

    chosen = {}
    for label, items in candidates.items():
        # Prefer PDFs first; then highest score
        pdfs = [it for it in items if it[2]]
        pool = pdfs if pdfs else items
        best = sorted(pool, key=lambda x: (-x[1], len(x[0])))[0]
        chosen[label] = best[0]
    return chosen

# -----------------------
# AUTO: discover sports
# -----------------------

def discover_sports(records: List[dict], exclude_prep: bool, prefer_domain: str = "") -> Dict[str, str]:
    """
    Return {sport_label: url} for each sport in SPORT_KEYWORDS that exists on site.
    Prefers HTML pages (not PDFs).
    """
    found = {}
    by_sport = defaultdict(list)

    for r in records:
        url = normalise_url(r["url"])
        title = r["title"] or ""
        text = r["text"] or ""
        if exclude_prep and any(h in url.lower() for h in EXCLUDE_PATH_HINTS):
            continue
        if is_pdf(url):
            continue  # prefer non-PDF for sport

        hay = " ".join([url.lower(), title.lower(), text.lower()[:500]])
        for sport, needles in SPORT_KEYWORDS.items():
            if contains_any(hay, [n.lower() for n in needles]):
                # score: prefer on-site + shorter path
                score = max(0, 120 - len(url))
                if prefer_domain and prefer_domain in url.lower():
                    score += 1.0
                by_sport[sport].append((url, score))

    for sport, items in by_sport.items():
        best = sorted(items, key=lambda x: (-x[1], len(x[0])))[0]
        # Prettify label: capitalise words
        label = " ".join(w.capitalize() for w in sport.split())
        found[label] = best[0]
    return found

# -----------------------
# Render final file
# -----------------------

HEADER_TEMPLATE = """# {school} – Static QA config (AUTO-GENERATED, aggressive)
# Do not edit by hand. Re-run generate_static_qa.py to refresh.
from typing import Dict, List

SITE_ROOT = "{site_root}"

# url_mapping anchors (core pages). Auto-generated from mapping + defaults in generator.
PAGE_LINKS: Dict[str, str] = {{
{page_links_block}
}}

def L(key: str) -> str:
    return PAGE_LINKS.get(key, SITE_ROOT)

"""

def make_page_links_block(page_links: Dict[str, str]) -> str:
    lines = []
    for k in sorted(page_links.keys()):
        v = page_links[k]
        lines.append(f'    "{k}": "{v}",')
    return "\n".join(lines)

def make_item_block(key: str, url_key_or_url: str, answer: str, label: str, variants: List[str], direct_url: bool=False) -> str:
    """
    If direct_url is False, url_key_or_url is a PAGE_LINKS key passed via L("key").
    If direct_url is True, url_key_or_url is a literal URL string.
    """
    url_field = (f'L("{url_key_or_url}")' if not direct_url else f'"{url_key_or_url}"')
    # Escape double quotes in strings
    def esc(s): return s.replace('"', '\\"')
    variants_list = "[" + ", ".join([f'"{esc(v)}"' for v in variants]) + "]"
    return (
f'''    {{
        "key": "{esc(key)}",
        "language": "en",
        "answer": "{esc(answer)}",
        "url": {url_field},
        "label": "{esc(label)}",
        "variants": {variants_list}
    }},'''
    )

def render_static_qa(
    school: str,
    site_root: str,
    url_mapping: Dict[str, str],
    records: List[dict],
    exclude_prep: bool,
    prefer_domain: str
) -> str:

    # 1) Core page links + curated items
    page_links = core_page_links(url_mapping, site_root, school)
    curated = core_static_items(school)

    # 2) Auto-discovered policies (key = clean label e.g. "First Aid Policy")
    policy_map = discover_policies(records, exclude_prep=exclude_prep, prefer_domain=prefer_domain)

    # 3) Auto-discovered sports (key = sport label e.g. "Rugby")
    sport_map = discover_sports(records, exclude_prep=exclude_prep, prefer_domain=prefer_domain)

    # Header
    out = []
    out.append(HEADER_TEMPLATE.format(
        school=school,
        site_root=site_root.rstrip("/"),
        page_links_block=make_page_links_block(page_links)
    ))

    out.append("\nSTATIC_QA_LIST = [\n")

    # Curated block (uses PAGE_LINKS via L("key"))
    for key, info in curated:
        out.append(make_item_block(
            key=key,
            url_key_or_url=key,   # uses PAGE_LINKS via L()
            answer=info["answer"],
            label=info["label"],
            variants=info["variants"],
            direct_url=False
        ))
        out.append("\n")

    # Auto policies block (direct URLs)
    # We generate safe variants from the label: base words + 'policy'
    for label, url in sorted(policy_map.items()):
        # Variant building
        base_words = [w for w in re.split(r"[^a-zA-Z]+", label) if w]
        base_lower = " ".join(base_words).lower()
        variants = list(set([
            label.lower(),
            base_lower,
            base_lower.replace(" policy", ""),
            base_lower.replace("policy", "").strip(),
            "policy " + base_lower.replace(" policy", "").strip(),
        ]))
        answer = f"Read the {label}."
        key = f"policy::{label.lower()}"
        out.append(make_item_block(
            key=key,
            url_key_or_url=url,   # direct URL
            answer=answer,
            label=label,
            variants=variants,
            direct_url=True
        ))
        out.append("\n")

    # Auto sports block (direct URLs)
    for sport_label, url in sorted(sport_map.items()):
        # Make friendly variants inc. boys/girls + team
        base = sport_label.lower()
        variants = list(set([
            base, f"{base} sport", f"{base} team", f"{base} fixtures",
            f"boys {base}", f"girls {base}",
            f"{base} at {school.lower()}",
        ]))
        answer = f"Find information about {sport_label} at {school}."
        key = f"sport::{base}"
        out.append(make_item_block(
            key=key,
            url_key_or_url=url,   # direct URL
            answer=answer,
            label=sport_label,
            variants=variants,
            direct_url=True
        ))
        out.append("\n")

    out.append("]\n")
    return "".join(out)

# -----------------------
# CLI
# -----------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapping", required=True, help="Path to url_mapping.py")
    ap.add_argument("--metadata", required=True, help="Path to metadata.pkl")
    ap.add_argument("--out", default="static_qa_config.py", help="Path to write static_qa_config.py")
    ap.add_argument("--school", required=True, help='School display name (e.g., "Cheltenham College")')
    ap.add_argument("--site-root", required=True, help='Root URL (e.g., "https://www.cheltenhamcollege.org/")')
    ap.add_argument("--prefer-domain", default="", help="Prefer URLs from this domain (e.g. cheltenhamcollege.org)")
    ap.add_argument("--exclude-prep", action="store_true", help="Exclude obvious prep/pre-prep areas")
    args = ap.parse_args()

    url_mapping = import_url_mapping(args.mapping)
    records = load_metadata(args.metadata)

    text = render_static_qa(
        school=args.school,
        site_root=args.site_root,
        url_mapping=url_mapping,
        records=records,
        exclude_prep=args.exclude_prep,
        prefer_domain=(args.prefer_domain or "")
    )

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✅ Wrote {args.out} for {args.school}")

if __name__ == "__main__":
    main()
