#!/usr/bin/env python3
"""
Cheltenham College scraper (Prep excluded) -> embeddings -> KB files
Now with stronger PDF harvesting & downloading.
"""

import os, re, time, json, pickle, argparse, logging, hashlib, requests, urllib.parse as up
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from dotenv import load_dotenv

# --------------------------------------------------------------------
# Globals
# --------------------------------------------------------------------
TARGET_TOKENS = 700
OVERLAP_TOKENS = 100
RATE_LIMIT_SLEEP = 0.5
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CollegeScraper/1.0; +https://bsmart-ai.com)"}

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def normalise_url(base: str, href: str) -> str:
    try: return up.urljoin(base, href.split("#")[0])
    except: return None

def matches_any(patterns, url: str) -> bool:
    return any(re.search(p, url) for p in patterns)

def is_same_site(url: str, allowed_domains) -> bool:
    return any(up.urlparse(url).netloc.endswith(d) for d in allowed_domains)

def retry_get(url: str, session: requests.Session, tries=2):
    for _ in range(tries):
        try: return session.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        except: time.sleep(1)
    return None

def looks_binary(url: str) -> bool:
    return any(url.lower().endswith(e) for e in [".jpg",".jpeg",".png",".gif",".mp4",".avi",".zip",".rar",".webp",".svg",".ico"])

def looks_document(url: str) -> str:
    for ext in ["pdf","docx"]:
        if url.lower().endswith("." + ext): return ext
    return ""

def size_ok(r: requests.Response, max_bytes=25 * 1024 * 1024) -> bool:
    try:
        if "Content-Length" in r.headers and int(r.headers["Content-Length"]) > max_bytes: return False
    except: pass
    try: return len(r.content) <= max_bytes
    except: return True

def is_prep_url(url: str) -> bool:
    u = url.lower(); return "/prep" in u or "pre-prep" in u

def is_college_pdf(url: str) -> bool:
    return not is_prep_url(url)

def sitemap_urls(root_url: str, session: requests.Session):
    base = f"{up.urlparse(root_url).scheme}://{up.urlparse(root_url).netloc}"
    for sm in ["/sitemap.xml","/sitemap_index.xml"]:
        u = base+sm
        try:
            r = session.get(u, timeout=8, headers=HEADERS)
            if r.ok and "xml" in r.headers.get("Content-Type","").lower():
                soup = BeautifulSoup(r.text,"xml")
                for loc in soup.find_all("loc"): yield loc.text.strip()
        except: continue

def ensure_dir(path: str): os.makedirs(path, exist_ok=True)

def safe_filename_from_url(url: str) -> str:
    parsed = up.urlparse(url); name=os.path.basename(parsed.path)
    if not name:
        stem=re.sub(r"[^A-Za-z0-9._-]+","_",parsed.path.strip("/")) or parsed.netloc or hashlib.md5(url.encode()).hexdigest()[:10]
        name=stem+".pdf" if not stem.lower().endswith(".pdf") else stem
    name=name.split("?")[0].split("&")[0]
    if not name.lower().endswith(".pdf"): name+=".pdf"
    return re.sub(r"[^\w.\-()+\s]","_",name)

def unique_path(directory, filename):
    base,ext=os.path.splitext(filename); candidate=os.path.join(directory,filename); i=2
    while os.path.exists(candidate): candidate=os.path.join(directory,f"{base}-{i}{ext}"); i+=1
    return candidate

def download_pdf(url, session, pdf_dir):
    ensure_dir(pdf_dir)
    r=retry_get(url,session,tries=3)
    if not r or not r.ok: return ""
    final_path=up.urlparse(r.url).path.lower(); ctype=(r.headers.get("Content-Type","") or "").lower()
    if "pdf" not in ctype and not final_path.endswith(".pdf") and not url.lower().endswith(".pdf"): return ""
    fname=safe_filename_from_url(r.url or url); fpath=unique_path(pdf_dir,fname)
    try:
        with open(fpath,"wb") as f: f.write(r.content)
        logging.info(f"Downloaded PDF: {fpath}"); return fpath
    except Exception as e: logging.warning(f"PDF write failed {url}: {e}"); return ""

def extract_pdf_text(local_pdf_path):
    try:
        import PyPDF2
        reader=PyPDF2.PdfReader(open(local_pdf_path,"rb"))
        return "\n".join([p.extract_text() or "" for p in reader.pages]).strip() or f"[PDF: {os.path.basename(local_pdf_path)}]"
    except: return f"[PDF: {os.path.basename(local_pdf_path)}]"

# --------------------------------------------------------------------
# Crawl
# --------------------------------------------------------------------
def harvest_pdfs_from_html(html, base_url):
    """Collect <a href=...pdf> and raw .pdf strings from HTML source"""
    found=set(); soup=BeautifulSoup(html,"html.parser")
    for a in soup.find_all("a", href=True):
        u=normalise_url(base_url,a["href"])
        if u and u.lower().endswith(".pdf"): found.add(u)
    # regex scan
    for m in re.findall(r'https?://[^\'"<> ]+\.pdf', html, flags=re.I): found.add(m)
    return list(found)

def collect_urls(root_url, allowed_domains, allow_patterns, exclude_patterns,
                 max_pages, max_depth, session, rp, ignore_robots=False):
    seen=set(); queue=[(root_url,0)]; collected=[]; base_root=f"{up.urlparse(root_url).scheme}://{up.urlparse(root_url).netloc}"
    for smu in sitemap_urls(root_url,session):
        u=normalise_url(base_root,smu); 
        if u: queue.append((u,1))
    while queue and len(collected)<max_pages:
        url,depth=queue.pop(0)
        if url in seen: continue
        seen.add(url)
        if is_prep_url(url) or not is_same_site(url,allowed_domains) or matches_any(exclude_patterns,url): continue
        if not ignore_robots and not rp.can_fetch(HEADERS["User-Agent"],url):
            if not rp.can_fetch("Mozilla/5.0",url): continue
        r=retry_get(url,session); time.sleep(RATE_LIMIT_SLEEP)
        if not r or not size_ok(r): continue
        ctype=(r.headers.get("Content-Type","").lower() or ""); final_path=up.urlparse(r.url).path.lower(); ext=looks_document(url)
        if "pdf" in ctype or final_path.endswith(".pdf") or url.lower().endswith(".pdf"):
            if is_college_pdf(url): collected.append(r.url)
        elif "docx" in ctype or ext=="docx": collected.append(r.url)
        elif "text/html" in ctype:
            collected.append(r.url)
            if depth<max_depth:
                pdfs=harvest_pdfs_from_html(r.text,r.url); collected.extend(pdfs)
                soup=BeautifulSoup(r.text,"html.parser")
                for a in soup.find_all("a",href=True):
                    u2=normalise_url(r.url,a["href"])
                    if not u2 or u2 in seen: continue
                    if is_prep_url(u2) or matches_any(exclude_patterns,u2) or not is_same_site(u2,allowed_domains): continue
                    if allow_patterns and depth>=1 and not matches_any(allow_patterns,u2): continue
                    queue.append((u2,depth+1))
    if not collected:
        r=retry_get(root_url,session)
        if r and "text/html" in (r.headers.get("Content-Type","").lower() or ""): collected=[root_url]
    logging.info(f"Collected {len(collected)} College URLs"); return collected

# --------------------------------------------------------------------
# Embedding stubs
# --------------------------------------------------------------------
def chunk_text(text, target_tokens=TARGET_TOKENS, overlap=OVERLAP_TOKENS):
    words=text.split(); 
    if not words: return []
    block=max(50,target_tokens-overlap); return [" ".join(words[i:i+target_tokens]) for i in range(0,len(words),block)]

def embed_texts(chunks): return [{"text":c,"embedding":[0.0]*10} for c in chunks]

# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------
def main():
    ap=argparse.ArgumentParser(description="Cheltenham College-only scraper (Prep excluded) -> embeddings -> KB files")
    ap.add_argument("--root",required=True); ap.add_argument("--domains",default=""); ap.add_argument("--allow",default=""); ap.add_argument("--exclude",default=""); ap.add_argument("--forced",default=""); ap.add_argument("--max_pages",type=int,default=1200); ap.add_argument("--max_depth",type=int,default=6); ap.add_argument("--outdir",default="kb_chunks"); ap.add_argument("--pdf_dir",default="downloads/pdfs"); ap.add_argument("--download_pdfs",action="store_true"); ap.add_argument("--ignore_robots",action="store_true"); ap.add_argument("--verbose",action="store_true")
    args=ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,format="%(levelname)s %(message)s")
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__),".env"))
    if not os.getenv("OPENAI_API_KEY"): logging.error("OPENAI_API_KEY not set"); return
    domains=[d.strip() for d in args.domains.split(",") if d.strip()] or [up.urlparse(args.root).netloc]
    allow_patterns=[p.strip() for p in args.allow.split(",") if p.strip()]
    exclude_patterns=[p.strip() for p in args.exclude.split(",") if p.strip()]
    session=requests.Session(); rp=RobotFileParser(); rp.set_url(up.urljoin(args.root,"/robots.txt"))
    try: rp.read()
    except: pass
    urls=collect_urls(args.root,domains,allow_patterns,exclude_patterns,args.max_pages,args.max_depth,session,rp,ignore_robots=args.ignore_robots)
    if args.forced:
        try: urls.extend([ln.strip() for ln in open(args.forced) if ln.strip()]); logging.info("Added forced URLs")
        except Exception as e: logging.warning(f"Could not read forced URLs file: {e}")
    seen=set(); deduped=[]; 
    for u in urls:
        if u not in seen: deduped.append(u); seen.add(u)
    urls=deduped
    if not urls: logging.error("No URLs collected"); return
    ensure_dir(args.outdir); 
    if args.download_pdfs: ensure_dir(args.pdf_dir)
    all_chunks=[]; pdf_map={}
    for u in urls:
        r=retry_get(u,session); 
        if not r or not r.ok: continue
        ctype=(r.headers.get("Content-Type","").lower() or ""); final_path=up.urlparse(r.url).path.lower()
        if "pdf" in ctype or final_path.endswith(".pdf") or u.lower().endswith(".pdf"):
            local_path=""
            if args.download_pdfs: 
                local_path=download_pdf(u,session,args.pdf_dir); 
                if local_path: pdf_map[u]=local_path
            text=extract_pdf_text(local_path) if local_path and os.path.exists(local_path) else f"[PDF] {u}"
        else:
            soup=BeautifulSoup(r.text,"html.parser")
            for tag in soup(["script","style","noscript"]): tag.decompose()
            text=soup.get_text(" ",strip=True)
        for c in chunk_text(text): all_chunks.append({"url":u,"text":c})
        time.sleep(RATE_LIMIT_SLEEP)
    if not all_chunks: logging.error("No chunks extracted"); return
    
    # Generate embeddings for all chunks
    embeddings_data = embed_texts([c["text"] for c in all_chunks])
    
    # Save chunks.jsonl
    with open(os.path.join(args.outdir,"chunks.jsonl"),"w",encoding="utf-8") as f:
        for ch in all_chunks: f.write(json.dumps(ch,ensure_ascii=False)+"\n")
    
    # Save doc_embeddings.pkl
    pickle.dump(embeddings_data,open(os.path.join(args.outdir,"doc_embeddings.pkl"),"wb"))
    
    # Save metadata.pkl
    metadata=[{"url":c["url"],"len":len(c["text"].split()),**({"local_pdf":pdf_map[c["url"]]} if c["url"] in pdf_map else {})} for c in all_chunks]
    pickle.dump(metadata,open(os.path.join(args.outdir,"metadata.pkl"),"wb"))
    
    # Create and save kb_chunks.pkl - consolidated knowledge base file
    kb_chunks = []
    for i, chunk in enumerate(all_chunks):
        kb_entry = {
            "id": i,
            "text": chunk["text"],
            "url": chunk["url"],
            "embedding": embeddings_data[i]["embedding"],
            "metadata": {
                "len": len(chunk["text"].split()),
                "chunk_index": i,
                "source_type": "pdf" if chunk["url"] in pdf_map else "html"
            }
        }
        # Add local PDF path if available
        if chunk["url"] in pdf_map:
            kb_entry["metadata"]["local_pdf"] = pdf_map[chunk["url"]]
        kb_chunks.append(kb_entry)
    
    # Save the consolidated kb_chunks.pkl file
    pickle.dump(kb_chunks, open(os.path.join(args.outdir, "kb_chunks.pkl"), "wb"))
    
    logging.info(f"Done: {len(all_chunks)} chunks")
    logging.info(f"Created kb_chunks.pkl with {len(kb_chunks)} entries")
    if args.download_pdfs: logging.info(f"PDFs saved under: {args.pdf_dir}")

if __name__=="__main__": main()