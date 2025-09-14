#!/usr/bin/env python3
"""
Cheltenham College scraper (Prep excluded) -> embeddings -> KB files
Now with direct PDF downloading (keeps original filenames).
"""

import os
import re
import time
import json
import pickle
import argparse
import logging
import hashlib
import requests
import urllib.parse as up

from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from dotenv import load_dotenv

# --------------------------------------------------------------------
# Globals and constants
# --------------------------------------------------------------------
TARGET_TOKENS = 700
OVERLAP_TOKENS = 100
RATE_LIMIT_SLEEP = 0.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CollegeScraper/1.0; +https://bsmart-ai.com)"
}

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def normalise_url(base: str, href: str) -> str:
    try:
        return up.urljoin(base, href.split("#")[0])
    except Exception:
        return None


def matches_any(patterns, url: str) -> bool:
    return any(re.search(p, url) for p in patterns)


def is_same_site(url: str, allowed_domains) -> bool:
    netloc = up.urlparse(url).netloc
    return any(netloc.endswith(d) for d in allowed_domains)


def retry_get(url: str, session: requests.Session, tries=2):
    for _ in range(tries):
        try:
            return session.get(url, headers=HEADERS, timeout=15)
        except Exception:
            time.sleep(1)
    return None


def looks_binary(url: str) -> bool:
    bad_ext = [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".avi", ".zip", ".rar", ".webp", ".svg", ".ico"]
    return any(url.lower().endswith(e) for e in bad_ext)


def looks_document(url: str) -> str:
    for ext in ["pdf", "docx"]:
        if url.lower().endswith("." + ext):
            return ext
    return ""


def size_ok(r: requests.Response, max_bytes=6 * 1024 * 1024) -> bool:
    # allow up to 6 MB per page by default
    if "Content-Length" in r.headers:
        try:
            if int(r.headers["Content-Length"]) > max_bytes:
                return False
        except Exception:
            pass
    try:
        return len(r.content) <= max_bytes
    except Exception:
        return True


def is_prep_url(url: str) -> bool:
    u = url.lower()
    return "/prep" in u or "pre-prep" in u or "/pre-prep" in u or "/pre-prep/" in u


def is_college_pdf(url: str) -> bool:
    # Keep fairly permissive: only exclude obvious prep
    if is_prep_url(url):
        return False
    return True


def sitemap_urls(root_url: str, session: requests.Session):
    # Try common sitemap paths
    base = f"{up.urlparse(root_url).scheme}://{up.urlparse(root_url).netloc}"
    for sm in ["/sitemap.xml", "/sitemap_index.xml"]:
        u = base + sm
        try:
            r = session.get(u, timeout=8, headers=HEADERS)
            if r.ok and "xml" in r.headers.get("Content-Type", "").lower():
                soup = BeautifulSoup(r.text, "xml")
                for loc in soup.find_all("loc"):
                    yield loc.text.strip()
        except Exception:
            continue


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def safe_filename_from_url(url: str) -> str:
    """
    Use the original last path segment if present; otherwise derive a sensible name.
    Keep the original extension if available.
    Only sanitise illegal filesystem characters.
    """
    parsed = up.urlparse(url)
    name = os.path.basename(parsed.path)  # may be '' if URL ends with '/'
    if not name:
        # derive from path or netloc + path hash
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.path.strip("/")) or parsed.netloc
        if not stem:
            stem = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
        name = f"{stem}.pdf" if not stem.lower().endswith(".pdf") else stem
    # strip query strings that some servers leave in the basename
    name = name.split("?")[0].split("&")[0]
    # ensure .pdf extension
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    # sanitise
    name = re.sub(r"[^\w.\-()+\s]", "_", name)
    return name


def unique_path(directory: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    i = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}-{i}{ext}")
        i += 1
    return candidate


def download_pdf(url: str, session: requests.Session, pdf_dir: str) -> str:
    """
    Download PDF to pdf_dir using original filename from URL.
    Returns the local file path on success, or '' on failure.
    """
    ensure_dir(pdf_dir)
    r = retry_get(url, session, tries=3)
    if not r or not r.ok:
        logging.warning(f"PDF download failed (no response): {url}")
        return ""
    ctype = (r.headers.get("Content-Type", "") or "").lower()
    if "pdf" not in ctype and not url.lower().endswith(".pdf"):
        logging.debug(f"Skipping download (not a pdf): {url} [{ctype}]")
        return ""
    fname = safe_filename_from_url(url)
    fpath = unique_path(pdf_dir, fname)
    try:
        with open(fpath, "wb") as f:
            f.write(r.content)
        logging.info(f"Downloaded PDF: {fpath}")
        return fpath
    except Exception as e:
        logging.warning(f"PDF write failed: {url} -> {e}")
        return ""


def extract_pdf_text(local_pdf_path: str) -> str:
    """
    Best-effort PDF text extraction.
    Tries PyPDF2; if unavailable or fails, returns a placeholder with the filename.
    """
    try:
        import PyPDF2  # type: ignore
        text_parts = []
        with open(local_pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                try:
                    text_parts.append(page.extract_text() or "")
                except Exception:
                    continue
        text = "\n".join(text_parts).strip()
        if text:
            return text
    except Exception:
        pass
    # Fallback
    logging.warning(f"PDF text extraction unavailable or failed: {os.path.basename(local_pdf_path)}")
    return f"[PDF: {os.path.basename(local_pdf_path)}]"


# --------------------------------------------------------------------
# Crawl
# --------------------------------------------------------------------
def collect_urls(root_url, allowed_domains, allow_patterns, exclude_patterns,
                 max_pages, max_depth, session, rp, ignore_robots=False):
    seen = set()
    queue = [(root_url, 0)]
    collected = []
    base_root = f"{up.urlparse(root_url).scheme}://{up.urlparse(root_url).netloc}"

    for smu in sitemap_urls(root_url, session):
        u = normalise_url(base_root, smu)
        if u:
            queue.append((u, 1))

    while queue and len(collected) < max_pages:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        if is_prep_url(url):
            logging.debug(f"skip (prep): {url}")
            continue
        if not is_same_site(url, allowed_domains):
            logging.debug(f"skip (off-domain): {url}")
            continue
        if matches_any(exclude_patterns, url):
            logging.debug(f"skip (exclude pattern): {url}")
            continue

        if not ignore_robots and not rp.can_fetch(HEADERS["User-Agent"], url):
            if not rp.can_fetch("Mozilla/5.0", url):
                logging.debug(f"skip (robots): {url}")
                continue

        r = retry_get(url, session)
        time.sleep(RATE_LIMIT_SLEEP)
        if not r:
            logging.debug(f"skip (no response): {url}")
            continue
        if not size_ok(r):
            logging.debug(f"skip (too large): {url}")
            continue

        ctype = (r.headers.get("Content-Type", "").lower() or "")
        ext = looks_document(url)

        if "application/pdf" in ctype or ext == "pdf" or url.lower().endswith(".pdf"):
            if is_college_pdf(url):
                collected.append(url)
        elif "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in ctype or ext == "docx":
            collected.append(url)
        elif "text/html" in ctype or (not looks_binary(url) and url.endswith("/")):
            collected.append(url)
            if depth < max_depth:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    u2 = normalise_url(url, a["href"])
                    if not u2 or u2 in seen:
                        continue
                    if is_prep_url(u2) or matches_any(exclude_patterns, u2) or not is_same_site(u2, allowed_domains):
                        continue
                    if allow_patterns and depth >= 1 and not matches_any(allow_patterns, u2):
                        continue
                    queue.append((u2, depth + 1))
        else:
            logging.debug(f"skip (unsupported ctype {ctype}): {url}")

    if not collected:
        r = retry_get(root_url, session)
        if r and "text/html" in (r.headers.get("Content-Type", "").lower() or ""):
            collected = [root_url]

    logging.info(f"Collected {len(collected)} College URLs")
    return collected


# --------------------------------------------------------------------
# Embedding stubs
# --------------------------------------------------------------------
def chunk_text(text, target_tokens=TARGET_TOKENS, overlap=OVERLAP_TOKENS):
    # Naive chunking by word count as a stand-in for token logic
    words = text.split()
    if not words:
        return []
    block = max(50, target_tokens - overlap)  # minimum safeguard
    chunks = []
    for i in range(0, len(words), block):
        chunks.append(" ".join(words[i:i + target_tokens]))
    return chunks


def embed_texts(chunks):
    # Placeholder for OpenAI embeddings (kept offline-safe)
    return [{"text": c, "embedding": [0.0] * 10} for c in chunks]


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------
def main():
    global TARGET_TOKENS, OVERLAP_TOKENS

    ap = argparse.ArgumentParser(
        description="Cheltenham College-only scraper (Prep excluded) -> embeddings -> KB files"
    )
    ap.add_argument("--root", required=True, help="Root URL (e.g. https://www.cheltenhamcollege.org/)")
    ap.add_argument("--domains", default="", help="Comma-separated allowed domains (blank = infer from root)")
    ap.add_argument("--allow", default="", help="Comma-separated regex allow patterns (optional)")
    ap.add_argument("--exclude", default="", help="Comma-separated regex exclude patterns")
    ap.add_argument("--forced", default="", help="Path to newline-delimited list of URLs to force-include")
    ap.add_argument("--max_pages", type=int, default=1200)
    ap.add_argument("--max_depth", type=int, default=6)
    ap.add_argument("--outdir", default="kb_chunks")
    ap.add_argument("--pdf_dir", default="downloads/pdfs", help="Where to save downloaded PDFs")
    ap.add_argument("--download_pdfs", action="store_true", help="Download PDFs locally using original filenames")
    ap.add_argument("--ignore_robots", action="store_true", help="Ignore robots.txt (use responsibly)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(message)s")

    # Load .env next to this file to avoid CWD issues
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OPENAI_API_KEY not set")
        return

    # Domains
    if args.domains:
        domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    else:
        domains = [up.urlparse(args.root).netloc]

    allow_patterns = [p.strip() for p in args.allow.split(",") if p.strip()]
    exclude_patterns = [p.strip() for p in args.exclude.split(",") if p.strip()]

    session = requests.Session()
    rp = RobotFileParser()
    rp.set_url(up.urljoin(args.root, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        pass

    urls = collect_urls(args.root, domains, allow_patterns, exclude_patterns,
                        args.max_pages, args.max_depth, session, rp,
                        ignore_robots=args.ignore_robots)

    # Forced URLs (always appended)
    if args.forced:
        try:
            with open(args.forced) as f:
                forced_urls = [ln.strip() for ln in f if ln.strip()]
                urls.extend(forced_urls)
                logging.info(f"Added {len(forced_urls)} forced URLs")
        except Exception as e:
            logging.warning(f"Could not read forced URLs file: {e}")

    # De-dup while preserving order
    deduped = []
    seen = set()
    for u in urls:
        if u not in seen:
            deduped.append(u)
            seen.add(u)
    urls = deduped

    if not urls:
        logging.error("No URLs collected")
        return

    ensure_dir(args.outdir)
    if args.download_pdfs:
        ensure_dir(args.pdf_dir)

    all_chunks = []
    pdf_map = {}  # url -> local_path

    for u in urls:
        r = retry_get(u, session)
        if not r or not r.ok:
            logging.debug(f"skip (fetch failed): {u}")
            continue

        ctype = (r.headers.get("Content-Type", "").lower() or "")
        if ("application/pdf" in ctype) or u.lower().endswith(".pdf"):
            local_path = ""
            if args.download_pdfs:
                local_path = download_pdf(u, session, args.pdf_dir)
                if local_path:
                    pdf_map[u] = local_path

            # Extract text if we have a local copy; otherwise minimal placeholder
            if local_path and os.path.exists(local_path):
                text = extract_pdf_text(local_path)
            else:
                text = f"[PDF] {u}"

        else:
            soup = BeautifulSoup(r.text, "html.parser")
            # remove script/style to improve text signal
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(" ", strip=True)

        chunks = chunk_text(text)
        for c in chunks:
            all_chunks.append({"url": u, "text": c})

        time.sleep(RATE_LIMIT_SLEEP)

    if not all_chunks:
        logging.error("No chunks extracted (after Prep exclusion)")
        return

    # Write chunks
    chunks_path = os.path.join(args.outdir, "chunks.jsonl")
    with open(chunks_path, "w", encoding="utf-8") as f:
        for ch in all_chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

    # Fake embeddings (stub)
    embeddings = embed_texts([c["text"] for c in all_chunks])
    with open(os.path.join(args.outdir, "doc_embeddings.pkl"), "wb") as f:
        pickle.dump(embeddings, f)

    # Metadata includes local PDF path if available
    metadata = []
    for c in all_chunks:
        m = {"url": c["url"], "len": len(c["text"].split())}
        if c["url"] in pdf_map:
            m["local_pdf"] = pdf_map[c["url"]]
        metadata.append(m)
    with open(os.path.join(args.outdir, "metadata.pkl"), "wb") as f:
        pickle.dump(metadata, f)

    logging.info(f"Done: {len(all_chunks)} chunks, {len(embeddings)} embeddings")
    if args.download_pdfs:
        logging.info(f"PDFs saved under: {args.pdf_dir}")


if __name__ == "__main__":
    main()
