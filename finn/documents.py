"""Bounded PDF fetches with public-host validation and page-preserving extraction."""
import hashlib
import io
import ipaddress
import socket
import re
from urllib.parse import urljoin, urlparse, parse_qs
import pdfplumber
import requests
from . import cache

HEADERS = {'User-Agent': 'Mozilla/5.0 (FINN research prototype)'}
MAX_BYTES = 25 * 1024 * 1024


def public_url(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Document links must use public HTTPS URLs.')
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Private document hosts are not allowed.')
    return url


def fetch_pdf(url):
    key = 'pdf:v2:' + hashlib.sha256(url.encode()).hexdigest()
    cached = cache.get(key, 86400)
    if cached is not None:
        return cached
    parsed = urlparse(url)
    # Screener sometimes links to BSE's HTML viewer instead of the PDF itself.
    if parsed.hostname == 'www.bseindia.com' and parsed.path.lower() == '/stockinfo/annpdfopen.aspx':
        name = parse_qs(parsed.query).get('Pname', [''])[0]
        if re.fullmatch(r'[A-Za-z0-9-]+\.pdf', name):
            url = 'https://www.bseindia.com/xml-data/corpfiling/AttachHis/' + name
    for _ in range(5):
        public_url(url)
        with requests.get(url, headers=HEADERS, timeout=(10, 45), stream=True, allow_redirects=False) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers['Location'])
                continue
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError('Document exceeds 25 MB limit.')
                chunks.append(chunk)
            raw = b''.join(chunks)
        if not raw.startswith(b'%PDF-'):
            raise ValueError('Source is not a readable PDF.')
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            if len(pdf.pages) > 600:
                raise ValueError('Document exceeds 600 page limit.')
            pages = [p.extract_text() or '' for p in pdf.pages]
        if not any(p.strip() for p in pages):
            raise ValueError('Scanned PDF has no extractable text; OCR is not included.')
        return cache.put(key, {'hash': hashlib.sha256(raw).hexdigest(), 'pages': pages, 'url': url})
    raise ValueError('Too many document redirects.')


def chunks(document, source_id, limit=14000):
    current = ''
    for page, text in enumerate(document['pages'], 1):
        for start in range(0, len(text), limit - 80):
            piece = f'[{source_id} p{page}] ' + text[start:start + limit - 80] + '\n'
            if len(current) + len(piece) > limit:
                yield current
                current = ''
            current += piece
    if current:
        yield current
