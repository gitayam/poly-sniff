import html
import re
import requests
from .config import RESEARCHTOOLS_URL


def _clean_text(text: str) -> str:
    """Decode HTML entities and normalize whitespace."""
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _split_compound(text: str) -> list[str]:
    """Split compound sentences on conjunctions, semicolons, and 'while/as' clauses."""
    parts = []
    for chunk in re.split(r'[;]|\s+while\s+|\s+as\s+(?=[A-Z])', text):
        chunk = chunk.strip().strip(',').strip()
        if len(chunk) >= 15:
            parts.append(chunk)
    return parts if len(parts) > 1 else [text]


def _extract_claims(title: str, description: str) -> list[str]:
    """Extract claim-like statements from title and description.

    Handles compound titles (split on ' as ', ' while '), HTML entities,
    and long description sentences by splitting on conjunctions.
    """
    claims = []
    seen = set()

    def _add(text: str):
        text = _clean_text(text)
        key = text.lower()
        if len(text) >= 10 and key not in seen:
            seen.add(key)
            claims.append(text)

    # Split compound titles: "X hits Y as Z announces W"
    if title:
        title = _clean_text(title)
        # Remove site name suffixes
        title = re.sub(r'\s*[:|]\s*(NPR|CNN|BBC|Reuters|AP News|The Guardian).*$', '', title)
        parts = _split_compound(title)
        for p in parts:
            _add(p)

    if description:
        description = _clean_text(description)
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', description)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15:
                continue
            # Split compound sentences
            for part in _split_compound(sentence):
                _add(part)

    return claims[:15]


def _extract_claims_via_api(url: str) -> list[dict] | None:
    """Try AI-powered claim extraction via researchtoolspy /api/tools/extract-claims."""
    try:
        resp = requests.post(
            f"{RESEARCHTOOLS_URL}/api/tools/extract-claims",
            json={"url": url},
            timeout=45,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get('claims', None)
    except requests.RequestException:
        pass
    return None


def extract_from_url(url: str) -> dict:
    """Extract claims from a URL via researchtoolspy.

    Tries AI-powered extraction first (/api/tools/extract-claims),
    falls back to metadata-based extraction (/api/tools/analyze-url).
    """
    # Try AI-powered claim extraction first
    ai_claims = _extract_claims_via_api(url)
    if ai_claims:
        claim_texts = [c.get('claim', c.get('text', '')) for c in ai_claims if c.get('claim') or c.get('text')]
        if claim_texts:
            print(f"  ai claims    : {len(claim_texts)}")
            return {
                'title': claim_texts[0],
                'description': '',
                'claims': claim_texts[:15],
                'source_url': url,
            }

    # Fall back to metadata-based extraction
    try:
        resp = requests.post(
            f"{RESEARCHTOOLS_URL}/api/tools/analyze-url",
            json={"url": url, "checkSEO": False},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        metadata = data.get('metadata', data)
        title = metadata.get('title', '')
        description = metadata.get('description', '')

        return {
            'title': _clean_text(title),
            'description': _clean_text(description),
            'claims': _extract_claims(title, description),
            'source_url': url,
        }
    except requests.RequestException as e:
        print(f"  Warning: Failed to analyze URL via researchtoolspy: {e}")
        print(f"  Falling back to URL as claim text.")
        return {
            'title': url,
            'description': '',
            'claims': [url],
            'source_url': url,
        }


def extract_from_text(claim_text: str) -> dict:
    """Wrap direct claim text into the standard claims format."""
    return {
        'title': claim_text,
        'description': '',
        'claims': [claim_text],
        'source_url': None,
    }
