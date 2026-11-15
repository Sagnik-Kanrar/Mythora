import html
import re
import uuid
from typing import List, Dict, Any, Optional, Set
from fastapi import APIRouter, HTTPException
from ..models import Character, CharacterCreate, CharacterUpdate
from ..services.db_service import db_service
from ..services.ai_service import ai_service

router = APIRouter(tags=["Characters"])

TITLES_HONORIFICS = {
    "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "miss", "dr", "dr.", 
    "doctor", "inspector", "detective", "captain", "lord", "lady",
    "sir", "madam", "madame", "master", "officer", "agent", "professor", "prof", "prof."
}

CONVERSATIONAL_PREFIXES = {
    "look", "see", "listen", "hey", "wait", "hello", "hi", "oh", "ah",
    "dekh", "dekho", "dekhi", "ruk", "ruko", "arre", "are", "areh", "arreh",
    "oye", "bhai", "bhaiya", "dada", "lekin", "par", "wah", "waah",
    "shun", "shuno", "sun", "suno", "bol", "bolo", "yaar", "yar"
}

NAME_SUFFIX_HONORIFICS = {
    "bhai", "bhaiya", "da", "dada", "di", "didi", "ji", "saheb", "sahib", "babu"
}

# Generic pronouns, filler phrases, and non-character colloquialisms
INVALID_ALIAS_WORDS = {
    "bhai", "tu", "tujh", "tera", "meri", "hum", "bro", "dude", "man", "guy",
    "he", "she", "him", "her", "they", "them", "you", "it", "i", "we", "us",
    "tera bhai", "mera bhai", "apna bhai", "mere bhai", "tere bhai"
}

NON_CHARACTER_WORDS = {
    "the", "this", "that", "these", "those", "there", "here", "then", "when", "after", "before", 
    "suddenly", "instead", "inside", "behind", "ahead", "every", "neither", "either", 
    "something", "nothing", "someone", "anyone", "everyone", "he", "she", "it", "they", 
    "we", "i", "you", "one", "who", "what", "where", "how", "why", "chapter", "manuscript", 
    "hooghly", "howrah", "calcutta", "railway", "dum", "catwalk", "station", "terminus",
    "navy", "colt", "british", "victorian", "river", "basin", "archives", "column", 
    "platform", "high", "quay", "street", "road", "house", "manor", "reverie", "key", "watch",
    "clock", "lantern", "tide", "ocean", "sea", "harbor", "order", "council", "society",
    "tower", "vault", "catacombs", "stone", "iron", "gold", "silver", "brass", "bronze",
    "autumn", "winter", "spring", "summer", "morning", "evening", "night", "midnight", "noon",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "october", "november", "december", "january", "february", "march", "april", "may",
    "june", "july", "august", "september", "north", "south", "east", "west",
    "door", "window", "carriage", "train", "ship", "boat", "mask", "cipher", "secret",
    "mystery", "crime", "truth", "darkness", "silence", "shadow", "light", "fog", "mist",
    "wind", "storm", "rain", "blood", "perhaps", "however", "although", "meanwhile", "finally",
    "soon", "never", "always", "often", "usually", "today", "yesterday", "tomorrow",
    "once", "twice", "several", "many", "few", "much", "little", "all", "some", "any",
    "none", "both", "each", "cliffside", "estate", "parlor", "chamber", "hall", "library",
    "ravenscar", "london", "hackathon", "commences", "last",
    "permanent", "draft", "entry", "permanent draft entry", "scene", "record", "scene record",
    "writing", "studio", "title", "summary", "status", "version", "revision", "page", "folio",
    "stained", "summons", "washed", "shadows", "dawn", "ruptured", "pacts", "subterranean", "spume",
    "in", "even", "beside", "along", "across", "under", "over", "between", "through", "against",
    # Game and system phrases
    "match", "starting", "game", "over", "press", "start", "loading", "ready", "level", "round",
    "player", "restart", "score", "online", "offline", "friends", "friend", "family", "peers",
    "buddies", "brother", "sister", "father", "mother", "childhood"
}

def clean_character_name(name: str) -> str:
    """
    Cleans leading conversational particles ('Dekh', 'Arre', 'Ruk', 'Oye') and
    trailing conversational suffixes ('bhai', 'da', 'ji') from a character candidate.
    """
    clean = re.sub(r'[\'\"”’‘“]', '', name).strip()
    words = clean.split()
    if not words:
        return ""
    # Strip leading conversational particles
    while words and words[0].lower() in CONVERSATIONAL_PREFIXES and len(words) > 1:
        words = words[1:]
    # Strip trailing suffix honorifics if preceded by a valid name
    if len(words) > 1 and words[-1].lower() in NAME_SUFFIX_HONORIFICS:
        words = words[:-1]
    return " ".join(words)

def normalize_name_tokens(name: str) -> List[str]:
    """Tokenize name removing punctuation and filtering out titles and conversational prefixes."""
    cleaned = clean_character_name(name)
    cleaned = re.sub(r"[^\w\s]", "", cleaned.lower())
    tokens = [t.strip() for t in cleaned.split() if t.strip()]
    return [t for t in tokens if t not in TITLES_HONORIFICS and t not in CONVERSATIONAL_PREFIXES]

def is_blacklisted_name(name: str) -> bool:
    clean = clean_character_name(name).strip().lower()
    if not clean or len(clean) < 2:
        return True
    if clean in NON_CHARACTER_WORDS or clean in INVALID_ALIAS_WORDS:
        return True
    tokens = normalize_name_tokens(clean)
    if not tokens:
        return True
    if all(t in NON_CHARACTER_WORDS for t in tokens):
        return True
    if clean.split()[0].lower() in {"in", "even", "from", "with", "at", "by", "on", "for"}:
        return True
    # If any token is match/game and another is starting/over/loading
    if len(tokens) >= 2 and any(t in {"match", "game", "round"} for t in tokens) and any(t in {"starting", "over", "loading", "ready"} for t in tokens):
        return True
    return False

def extract_manuscript_alias_clusters(text: str) -> Dict[str, Set[str]]:
    """
    Manuscript Alias & Nickname Cluster Analysis:
    Discovers explicit nickname declarations, parenthetical names, alias introductions,
    and dialogue co-reference patterns across the manuscript.
    """
    clusters: Dict[str, Set[str]] = {}

    def link(name1: str, name2: str):
        c1 = clean_character_name(name1)
        c2 = clean_character_name(name2)
        if not c1 or not c2 or not c1[0].isupper() or not c2[0].isupper() or c1.lower() == c2.lower():
            return
        if is_blacklisted_name(c1) or is_blacklisted_name(c2):
            return
        t1, t2 = c1.lower(), c2.lower()
        set1 = clusters.get(t1, {c1})
        set2 = clusters.get(t2, {c2})
        merged = set1.union(set2)
        for k in merged:
            clusters[k.lower()] = merged

    # 1. Nickname—as ... called Name
    p1 = r'\b([A-Z][a-z]+)[—–\s-]+as\s+(?:(?:his|her|their|our|my|all)\s+)?(?:(?:childhood|boyhood|girlhood|old|close|intimate|fellow|school)\s+)?(?:friends|family|peers|buddies|companions|relatives)?\s*(?:called|named|knew|dubbed)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
    for m in re.finditer(p1, text):
        link(m.group(1), m.group(2))

    # 2. Name, (also) known as / nicknamed / called / went by Nickname
    p2 = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\s]+(?:also\s+)?(?:known\s+as|nicknamed|called|went\s+by|dubbed)\s+(?:["\']?)([A-Z][a-z]+)(?:["\']?)\b'
    for m in re.finditer(p2, text, re.IGNORECASE):
        link(m.group(1), m.group(2))

    # 3. Name (Nickname)
    p3 = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\(([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\)'
    for m in re.finditer(p3, text):
        link(m.group(1), m.group(2))

    # 4. First name "Nickname" Last name
    p4 = r'\b([A-Z][a-z]+)\s+["\']([A-Z][a-z]+)["\']\s+([A-Z][a-z]+)\b'
    for m in re.finditer(p4, text):
        full = f"{m.group(1)} {m.group(3)}"
        nick = m.group(2)
        link(full, nick)
        link(m.group(1), nick)

    return clusters

def sanitize_character_aliases(
    char_name: str,
    aliases: List[str],
    all_character_names: Optional[List[str]] = None,
    alias_clusters: Optional[Dict[str, Set[str]]] = None
) -> List[str]:
    """
    Cleans and deduplicates aliases:
    - Strips invalid words, filler pronouns, conversational prefixes/suffixes.
    - Prevents alias collision with other distinct characters in the story (unless linked by alias clusters).
    """
    clean_canon = clean_character_name(char_name)
    canon_tokens = set(normalize_name_tokens(clean_canon))
    other_distinct_names = set()
    if all_character_names:
        for oname in all_character_names:
            oclean = clean_character_name(oname)
            otokens = set(normalize_name_tokens(oclean))
            if not (otokens & canon_tokens):
                other_distinct_names.add(oclean.lower())
                for t in otokens:
                    other_distinct_names.add(t)

    # If alias clusters link any name to this character, that name is an alias, not a distinct character
    if alias_clusters:
        linked_names = set()
        for cand_key in [clean_canon.lower()] + list(canon_tokens):
            if cand_key in alias_clusters:
                for ln in alias_clusters[cand_key]:
                    cln = clean_character_name(ln).lower()
                    linked_names.add(cln)
                    for t in normalize_name_tokens(cln):
                        linked_names.add(t)
        for ln in linked_names:
            other_distinct_names.discard(ln)

    sanitized = []
    for a in aliases:
        if not a:
            continue
        clean_a = clean_character_name(a)
        a_lower = clean_a.lower()
        if not clean_a or len(clean_a) < 2:
            continue
        if is_blacklisted_name(clean_a) or a_lower in INVALID_ALIAS_WORDS:
            continue
        if any(inv in a_lower.split() for inv in ["tera", "mera", "apna", "tujh", "tu", "bhai", "yaar", "bro", "dude"]):
            tokens_a = normalize_name_tokens(clean_a)
            if not tokens_a:
                continue
        if a_lower in other_distinct_names:
            continue
        if a_lower == clean_canon.lower():
            continue
        if a_lower not in [x.lower() for x in sanitized]:
            sanitized.append(clean_a)
    return sanitized

def verify_character_in_text(candidate_name: str, text: str) -> Optional[str]:
    """
    Strict Verification:
    Ensures that the candidate character is genuinely mentioned in the text.
    Extracts the verbatim supporting sentence from the text.
    Returns the evidence sentence if verified, or None if hallucinated/unsupported.
    """
    clean_name = clean_character_name(candidate_name)
    if is_blacklisted_name(clean_name):
        return None

    tokens = normalize_name_tokens(clean_name)
    distinctive = [t for t in tokens if t not in NON_CHARACTER_WORDS]
    if not distinctive:
        return None

    # Distinctive token check: at least one distinctive token must appear as whole word in text
    has_token = False
    for t in distinctive:
        if re.search(rf'\b{re.escape(t)}\b', text, re.IGNORECASE):
            has_token = True
            break
    if not has_token:
        return None

    sentences = re.split(r'(?<=[.!?])\s+', text)
    # 1. Full name match priority
    for s in sentences:
        if re.search(rf'\b{re.escape(clean_name)}\b', s, re.IGNORECASE):
            return s.strip()

    # 2. First distinctive token match priority (e.g. given name)
    first_token = distinctive[0]
    for s in sentences:
        if re.search(rf'\b{re.escape(first_token)}\b', s, re.IGNORECASE):
            return s.strip()

    # 3. Any distinctive token match
    for s in sentences:
        for t in distinctive:
            if re.search(rf'\b{re.escape(t)}\b', s, re.IGNORECASE):
                return s.strip()

    return None

def resolve_character_identity(
    candidate_name: str,
    candidate_aliases: List[str],
    existing_characters: List[Dict[str, Any]],
    context_text: str = "",
    alias_clusters: Optional[Dict[str, Set[str]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Intelligent Entity Resolution System:
    1. Exact canonical name match (case-insensitive, conversational-prefix cleaned).
    2. Token-based match:
       - Multi-token full names match single-token first names or surnames.
       - Single-token references match unique multi-token canonical characters.
       - Disambiguates shared surnames (e.g. Lord Alistair Blackwood vs Lady Evelyn Blackwood).
    3. Manuscript alias clusters (e.g. Boni <-> Saptarshi Chowdhury).
    4. Exact alias match with cross-character collision protection.
    5. Never merges distinct characters who share only a surname or first name with different identities.
    """
    cleaned_name = clean_character_name(candidate_name)
    c_lower = cleaned_name.lower()
    if not c_lower or is_blacklisted_name(cleaned_name):
        return None

    cand_tokens = normalize_name_tokens(cleaned_name)
    if not cand_tokens:
        return None

    cleaned_cand_aliases = []
    for a in candidate_aliases:
        ca = clean_character_name(a)
        if ca and not is_blacklisted_name(ca) and ca.lower() not in INVALID_ALIAS_WORDS:
            cleaned_cand_aliases.append(ca)

    all_cand_names = [c_lower] + [a.lower() for a in cleaned_cand_aliases]

    if alias_clusters:
        for name_key in list(all_cand_names):
            if name_key in alias_clusters:
                for clustered_name in alias_clusters[name_key]:
                    cl_clean = clean_character_name(clustered_name).lower()
                    if cl_clean and cl_clean not in all_cand_names and not is_blacklisted_name(cl_clean):
                        all_cand_names.append(cl_clean)

    # Stage 1: Exact Name Match
    for ex in existing_characters:
        ex_clean = clean_character_name(ex.get("name", ""))
        ex_lower = ex_clean.lower()
        if c_lower == ex_lower:
            return ex

    # Stage 2: Token-based match (Full Name <-> First/Surname)
    token_matches = []
    for ex in existing_characters:
        ex_clean = clean_character_name(ex.get("name", ""))
        ex_tokens = normalize_name_tokens(ex_clean)
        if not ex_tokens:
            continue

        if cand_tokens == ex_tokens:
            token_matches.append((ex, "exact_tokens"))
            continue

        # Candidate is multi-token ("Saptarshi Chowdhury"), existing is single token ("Saptarshi" or "Chowdhury")
        if len(cand_tokens) > 1 and len(ex_tokens) == 1:
            ex_token = ex_tokens[0]
            if ex_token in cand_tokens:
                other_with_token = [
                    o for o in existing_characters
                    if o.get("id") != ex.get("id") and ex_token in normalize_name_tokens(clean_character_name(o.get("name", "")))
                ]
                if not other_with_token:
                    token_matches.append((ex, "token_subset"))

        # Candidate is single-token ("Saptarshi" or "Chowdhury"), existing is multi-token ("Saptarshi Chowdhury")
        elif len(cand_tokens) == 1 and len(ex_tokens) > 1:
            c_token = cand_tokens[0]
            if c_token in ex_tokens:
                # Ensure no other character shares this token (e.g. shared surname check)
                other_with_token = [
                    o for o in existing_characters
                    if o.get("id") != ex.get("id") and c_token in normalize_name_tokens(clean_character_name(o.get("name", "")))
                ]
                if not other_with_token:
                    token_matches.append((ex, "token_superset"))

    if len(token_matches) >= 1:
        return token_matches[0][0]

    # Stage 3: Manuscript Alias Clusters (e.g. Boni <-> Saptarshi Chowdhury)
    if alias_clusters:
        for ex in existing_characters:
            ex_clean = clean_character_name(ex.get("name", ""))
            ex_tokens = normalize_name_tokens(ex_clean)
            for cand_n in all_cand_names:
                if cand_n in alias_clusters:
                    clustered_names = {clean_character_name(cn).lower() for cn in alias_clusters[cand_n]}
                    if ex_clean.lower() in clustered_names or any(t in clustered_names for t in ex_tokens):
                        return ex

    # Stage 4: Known Verified Aliases Match
    other_primary_tokens = set()
    for ex in existing_characters:
        for t in normalize_name_tokens(clean_character_name(ex.get("name", ""))):
            other_primary_tokens.add(t)

    for ex in existing_characters:
        ex_clean = clean_character_name(ex.get("name", ""))
        ex_tokens = normalize_name_tokens(ex_clean)
        ex_aliases = [clean_character_name(a).lower() for a in (ex.get("aliases") or []) if a and a.strip().lower() not in INVALID_ALIAS_WORDS]
        if ex.get("alias") and ex.get("alias").strip().lower() not in INVALID_ALIAS_WORDS:
            ex_aliases.append(clean_character_name(ex.get("alias", "")).lower())

        if c_lower in ex_aliases:
            if any(t in ex_tokens for t in cand_tokens) or not any(t in other_primary_tokens for t in cand_tokens if t not in ex_tokens):
                return ex

        for cand_a in cleaned_cand_aliases:
            if cand_a.lower() in ex_aliases or cand_a.lower() == ex_clean.lower():
                cand_a_tokens = normalize_name_tokens(cand_a)
                if any(t in ex_tokens for t in cand_a_tokens) or not any(t in other_primary_tokens for t in cand_a_tokens if t not in ex_tokens):
                    return ex

    return None

VALID_NARRATIVE_STATUSES = {
    "Alive", "Presumed dead", "Deceased", "Missing", "Unknown", 
    "Injured", "Resurrected / returned", "Unconfirmed"
}

def record_character_status_transition(
    char: Dict[str, Any],
    new_status: str,
    chapter_num: int,
    evidence_text: str = "",
    status_type: str = "explicit"
) -> bool:
    clean_status = new_status.strip().capitalize() if new_status else "Alive"
    lower_s = clean_status.lower()
    if "presumed" in lower_s or "thought dead" in lower_s:
        clean_status = "Presumed dead"
    elif "dead" in lower_s or "deceased" in lower_s or "killed" in lower_s:
        clean_status = "Deceased"
    elif "missing" in lower_s or "lost" in lower_s:
        clean_status = "Missing"
    elif "injured" in lower_s or "wounded" in lower_s:
        clean_status = "Injured"
    elif "resurrect" in lower_s or "returned" in lower_s:
        clean_status = "Resurrected / returned"
    elif "unconfirmed" in lower_s:
        clean_status = "Unconfirmed"
    elif "alive" in lower_s:
        clean_status = "Alive"
    elif clean_status not in VALID_NARRATIVE_STATUSES:
        clean_status = "Unknown"

    history = char.get("status_history", [])
    current_status = char.get("current_status", "Alive")

    if current_status != clean_status or not history:
        history.append({
            "status": clean_status,
            "chapter": chapter_num,
            "evidence": evidence_text[:300] if evidence_text else f"Observed in Chapter {chapter_num}",
            "type": status_type
        })
        char["status_history"] = history
        char["current_status"] = clean_status
        return True
    return False

@router.get("/api/stories/{story_id}/characters", response_model=List[Character])
def get_story_characters(story_id: str):
    return db_service.get_characters(story_id)

@router.post("/api/stories/{story_id}/characters/sync")
def sync_characters_from_manuscript(story_id: str):
    """
    Strict Manuscript Character Synchronization:
    Analyzes ONLY actual saved chapters and folios from the Writing Studio.
    Extracts ONLY real story characters with direct textual evidence.
    No hypothetical, imaginary, AI-invented, or suggested characters.
    Merges aliases, preserves author classifications, and returns added, updated, unchanged counts.
    Ensures ONE PERSON = ONE CHARACTER DOSSIER with canonical full names and aliases.
    """
    story = db_service.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    genre = story.get("genre", "Fiction")
    chapters = db_service.get_chapters(story_id)
    if not chapters:
        existing_chars = db_service.get_characters(story_id)
        return {
            "synced_count": 0,
            "added_count": 0,
            "updated_count": 0,
            "unchanged_count": len(existing_chars),
            "new_characters": [],
            "characters": existing_chars
        }

    # Step 1: Pre-clean and consolidate any existing duplicate cards
    dedupe_pre = deduplicate_story_characters(story_id)
    existing_chars = dedupe_pre.get("characters") or db_service.get_characters(story_id)

    # Step 2: Build full story text to discover manuscript alias/nickname clusters
    sorted_chapters = sorted(chapters, key=lambda c: c.get("chapter_number", 0))
    full_text_parts = []
    chapter_text_map = {}

    for chap in sorted_chapters:
        c_num = chap.get("chapter_number", 1)
        chap_id = chap.get("id", "")
        content = chap.get("content", "").strip()

        chap_pages = db_service.get_pages(chap_id)
        if chap_pages:
            combined_pages = " ".join([p.get("content", "") for p in chap_pages if p.get("content") and p.get("content").strip() not in ["", "<p><br></p>"]])
            if len(combined_pages.strip()) > len(content):
                content = combined_pages

        clean_text = re.sub(r'<[^>]+>', ' ', content)
        clean_text = html.unescape(clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        chapter_text_map[c_num] = clean_text
        if clean_text:
            full_text_parts.append(clean_text)

    full_manuscript_text = " ".join(full_text_parts)
    alias_clusters = extract_manuscript_alias_clusters(full_manuscript_text)

    newly_added = []
    updated_chars = []
    updated_ids = set()

    for chap in sorted_chapters:
        c_num = chap.get("chapter_number", 1)
        clean_text = chapter_text_map.get(c_num, "")
        if len(clean_text) < 20:
            continue

        all_known = existing_chars + newly_added
        extracted = ai_service.extract_characters_from_text(
            text=clean_text,
            existing_characters=all_known,
            story_genre=genre
        )

        for item in extracted:
            raw_name = item.get("name", "").strip()
            c_name = clean_character_name(raw_name)
            if not c_name or is_blacklisted_name(c_name):
                continue

            # Strict verification: candidate MUST exist in the actual text
            evidence_text = verify_character_in_text(c_name, clean_text)
            if not evidence_text:
                continue

            raw_aliases = list(item.get("aliases", []))
            if item.get("alias") and item.get("alias") not in raw_aliases:
                raw_aliases.append(item.get("alias"))
            c_aliases = [clean_character_name(a) for a in raw_aliases if clean_character_name(a) and not is_blacklisted_name(clean_character_name(a))]

            matched = resolve_character_identity(
                candidate_name=c_name,
                candidate_aliases=c_aliases,
                existing_characters=all_known,
                context_text=clean_text,
                alias_clusters=alias_clusters
            )

            if matched:
                modified = False

                # If candidate or cluster has a fuller canonical name, upgrade the existing character name
                cand_tokens = normalize_name_tokens(c_name)
                ex_tokens = normalize_name_tokens(matched.get("name", ""))
                target_canon_name = c_name
                if len(cand_tokens) <= len(ex_tokens):
                    target_canon_name = matched.get("name", "")

                # Check if alias cluster offers an even fuller canonical name
                clean_target_lower = target_canon_name.lower()
                if clean_target_lower in alias_clusters:
                    cluster_candidates = sorted(list(alias_clusters[clean_target_lower]), key=lambda x: (len(normalize_name_tokens(x)), len(x)), reverse=True)
                    if cluster_candidates:
                        fullest_in_cluster = clean_character_name(cluster_candidates[0])
                        if len(normalize_name_tokens(fullest_in_cluster)) > len(normalize_name_tokens(target_canon_name)):
                            target_canon_name = fullest_in_cluster

                if target_canon_name != matched.get("name", ""):
                    old_name = matched.get("name", "")
                    matched["name"] = target_canon_name
                    if old_name and old_name.lower() != target_canon_name.lower():
                        cur_aliases = list(matched.get("aliases", []))
                        if old_name.lower() not in [a.lower() for a in cur_aliases]:
                            cur_aliases.append(old_name)
                            matched["aliases"] = cur_aliases
                    modified = True

                # Merge aliases safely
                existing_aliases = list(matched.get("aliases", []))
                merged_aliases_pool = existing_aliases + c_aliases
                if c_name.lower() != matched["name"].lower() and c_name.lower() not in [x.lower() for x in merged_aliases_pool]:
                    merged_aliases_pool.append(c_name)

                if alias_clusters:
                    cand_keys = [matched["name"].lower(), c_name.lower()] + normalize_name_tokens(matched["name"]) + normalize_name_tokens(c_name)
                    for k in cand_keys:
                        if k in alias_clusters:
                            for cl_name in alias_clusters[k]:
                                cl_clean = clean_character_name(cl_name)
                                if cl_clean and not is_blacklisted_name(cl_clean) and cl_clean.lower() != matched["name"].lower():
                                    if cl_clean.lower() not in [x.lower() for x in merged_aliases_pool]:
                                        merged_aliases_pool.append(cl_clean)

                all_raw_known_names = [c.get("name", "") for c in all_known]
                sanitized_aliases = sanitize_character_aliases(
                    char_name=matched["name"],
                    aliases=merged_aliases_pool,
                    all_character_names=all_raw_known_names,
                    alias_clusters=alias_clusters
                )
                if sanitized_aliases != matched.get("aliases"):
                    matched["aliases"] = sanitized_aliases
                    modified = True

                # Update appearances & evidence
                matched["last_appearance"] = f"Chapter {c_num}"
                ex_evidence = list(matched.get("evidence", []))
                if not any(e.get("chapter") == c_num for e in ex_evidence):
                    ex_evidence.append({"chapter": c_num, "text": evidence_text[:300]})
                    matched["evidence"] = ex_evidence
                    modified = True

                # Record status transition if present
                if item.get("status"):
                    status_changed = record_character_status_transition(
                        matched,
                        new_status=item["status"],
                        chapter_num=c_num,
                        evidence_text=evidence_text[:250],
                        status_type="explicit"
                    )
                    if status_changed:
                        modified = True

                # Merge personality traits
                new_traits = item.get("personality_traits", [])
                if new_traits:
                    cur_traits = list(matched.get("personality_traits", []))
                    for t in new_traits:
                        if t and t not in cur_traits:
                            cur_traits.append(t)
                            modified = True
                    matched["personality_traits"] = cur_traits

                # Retain or enrich physical description if empty
                if not matched.get("physical_description") and item.get("physical_description"):
                    matched["physical_description"] = item["physical_description"]
                    modified = True

                # NEVER OVERWRITE investigation_status (Person of Interest, Innocent, Culprit, Unclassified)
                # NEVER OVERWRITE manually written backstory if non-empty

                if modified:
                    db_service.save_character(matched)
                    if matched["id"] not in updated_ids:
                        updated_ids.add(matched["id"])
                        updated_chars.append(matched)

            else:
                # Add genuinely new character who appears in the story
                char_id = f"char_{uuid.uuid4().hex[:10]}"
                raw_status = item.get("status", "Alive")
                init_history = [{
                    "status": raw_status,
                    "chapter": c_num,
                    "evidence": f"Introduced in Chapter {c_num}: {evidence_text[:200]}",
                    "type": "explicit"
                }]

                # Check if alias cluster offers an even fuller canonical name for new character
                canonical_new_name = c_name
                clean_cand_lower = c_name.lower()
                if clean_cand_lower in alias_clusters:
                    cluster_candidates = sorted(list(alias_clusters[clean_cand_lower]), key=lambda x: (len(normalize_name_tokens(x)), len(x)), reverse=True)
                    if cluster_candidates:
                        fullest_in_cluster = clean_character_name(cluster_candidates[0])
                        if len(normalize_name_tokens(fullest_in_cluster)) > len(normalize_name_tokens(canonical_new_name)):
                            canonical_new_name = fullest_in_cluster

                pool_aliases = list(c_aliases)
                if c_name.lower() != canonical_new_name.lower():
                    pool_aliases.append(c_name)

                if alias_clusters:
                    cand_keys = [canonical_new_name.lower(), c_name.lower()] + normalize_name_tokens(canonical_new_name) + normalize_name_tokens(c_name)
                    for k in cand_keys:
                        if k in alias_clusters:
                            for cl_name in alias_clusters[k]:
                                cl_clean = clean_character_name(cl_name)
                                if cl_clean and not is_blacklisted_name(cl_clean) and cl_clean.lower() != canonical_new_name.lower():
                                    if cl_clean.lower() not in [x.lower() for x in pool_aliases]:
                                        pool_aliases.append(cl_clean)

                all_raw_known_names = [c.get("name", "") for c in all_known]
                sanitized_new_aliases = sanitize_character_aliases(
                    char_name=canonical_new_name,
                    aliases=pool_aliases,
                    all_character_names=all_raw_known_names,
                    alias_clusters=alias_clusters
                )

                new_char = {
                    "id": char_id,
                    "story_id": story_id,
                    "name": canonical_new_name,
                    "alias": item.get("alias", ""),
                    "aliases": sanitized_new_aliases,
                    "age": str(item.get("age", "")),
                    "role": item.get("role", "Supporting Character"),
                    "personality_traits": item.get("personality_traits", ["Observant", "Determined"]),
                    "physical_description": item.get("physical_description", ""),
                    "backstory": evidence_text[:300],
                    "motivations": item.get("motivations", ""),
                    "goals": item.get("goals", ""),
                    "fears": item.get("fears", ""),
                    "secrets": item.get("secrets", ""),
                    "current_status": raw_status,
                    "status_history": init_history,
                    "first_appearance": f"Chapter {c_num}",
                    "last_appearance": f"Chapter {c_num}",
                    "relationships": [],
                    "evidence": [{"chapter": c_num, "text": evidence_text[:300]}],
                    "investigation_status": "unclassified",
                    "confidence": 1.0
                }
                db_service.save_character(new_char)
                newly_added.append(new_char)

    # Step 3: Run post-sync atomic deduplication pass to ensure full graph consolidation
    final_dedupe = deduplicate_story_characters(story_id)
    all_current = final_dedupe.get("characters") or db_service.get_characters(story_id)
    unchanged_count = max(0, len(existing_chars) - len(updated_chars))

    return {
        "synced_count": len(newly_added),
        "added_count": len(newly_added),
        "updated_count": len(updated_chars),
        "unchanged_count": unchanged_count,
        "new_characters": newly_added,
        "characters": all_current
    }

@router.post("/api/stories/{story_id}/characters", response_model=Character)
@router.post("/api/characters", response_model=Character)
def create_character(data: CharacterCreate, story_id: str = None):
    data_dict = data.dict()
    sid = story_id or data_dict.get("story_id")
    if not sid:
        raise HTTPException(status_code=400, detail="story_id is required")
    data_dict["story_id"] = sid
    if "investigationStatus" in data_dict and not data_dict.get("investigation_status"):
        data_dict["investigation_status"] = data_dict["investigationStatus"]
    data_dict["id"] = f"char_{uuid.uuid4().hex[:10]}"
    return db_service.save_character(data_dict)

@router.get("/api/characters/{character_id}", response_model=Character)
def get_character(character_id: str):
    char = db_service.get_character(character_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character dossier not found")
    return char

@router.put("/api/characters/{character_id}", response_model=Character)
def update_character(character_id: str, data: CharacterUpdate):
    existing = db_service.get_character(character_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Character dossier not found")
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    existing.update(update_data)
    return db_service.save_character(existing)

@router.put("/api/characters/{character_id}/investigation-status", response_model=Character)
def update_character_investigation_status(character_id: str, payload: Dict[str, Any]):
    status = payload.get("investigation_status", "unclassified")
    valid_statuses = {"innocent", "person_of_interest", "unclassified"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid investigation status '{status}'. Valid options: innocent, person_of_interest, unclassified."
        )
    existing = db_service.get_character(character_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Character dossier not found")
    existing["investigation_status"] = status
    return db_service.save_character(existing)

@router.delete("/api/characters/{character_id}")
def delete_character(character_id: str):
    success = db_service.delete_character(character_id)
    return {"success": success, "deleted_id": character_id}

@router.post("/api/characters/generate")
def generate_ai_character(params: Dict[str, Any]):
    genre = params.get("genre", "Mystery")
    role = params.get("role", "Protagonist")
    theme = params.get("theme", "")
    profile = ai_service.generate_character(genre, role, theme)
    return {"character": profile}

@router.get("/api/stories/{story_id}/board")
def get_story_board(story_id: str):
    board = db_service.get_board(story_id)
    if not board:
        return {"story_id": story_id, "positions": {}, "connections": []}
    return board

@router.put("/api/stories/{story_id}/board")
def update_story_board(story_id: str, board_data: Dict[str, Any]):
    return db_service.save_board(story_id, board_data)

def deduplicate_character_entities_helper(
    chars: List[Dict[str, Any]], 
    board: Dict[str, Any],
    alias_clusters: Optional[Dict[str, Set[str]]] = None
):
    """
    Pure in-memory deduplication and board remapping helper for character entities.
    Consolidates variant duplicate records into the fullest canonical name.
    Preserves all unique character information, appearances, traits, status histories,
    and board relationships losslessly.
    """
    chars_copy = [dict(c) for c in chars]
    
    # Filter out blacklisted/non-character entities and sanitize clean names upfront
    valid_chars = []
    purged_ids = []
    all_raw_names = [c.get("name", "") for c in chars_copy]

    for c in chars_copy:
        raw_name = c.get("name", "").strip()
        cleaned = clean_character_name(raw_name)
        if not cleaned or is_blacklisted_name(cleaned):
            purged_ids.append(c["id"])
            continue
        c["name"] = cleaned
        c["aliases"] = sanitize_character_aliases(
            char_name=cleaned,
            aliases=c.get("aliases") or [],
            all_character_names=all_raw_names,
            alias_clusters=alias_clusters
        )
        valid_chars.append(c)

    # Sort characters with longest full names first so canonical identity anchors to the complete name
    valid_chars.sort(key=lambda c: (len(normalize_name_tokens(c.get("name", ""))), len(c.get("name", ""))), reverse=True)

    canonical_list = []
    alias_to_canonical = {}

    for c in valid_chars:
        name = c.get("name", "").strip()
        aliases = c.get("aliases") or []
        if c.get("alias") and c.get("alias") not in aliases:
            aliases.append(c.get("alias"))

        # Find matching canonical character already selected
        matched_canon = None
        for cc in canonical_list:
            if cc.get("id") == c.get("id"):
                continue
            if resolve_character_identity(name, aliases, [cc], alias_clusters=alias_clusters):
                matched_canon = cc
                break

        if matched_canon:
            alias_to_canonical[c["id"]] = matched_canon["id"]
            purged_ids.append(c["id"])

            # Upgrade canon name if candidate has more tokens or cluster provides fuller name
            c_tokens = normalize_name_tokens(name)
            canon_tokens = normalize_name_tokens(matched_canon.get("name", ""))
            if len(c_tokens) > len(canon_tokens):
                old_canon_name = matched_canon.get("name", "")
                if old_canon_name and old_canon_name.lower() not in [a.lower() for a in matched_canon.get("aliases", [])]:
                    matched_canon.setdefault("aliases", []).append(old_canon_name)
                matched_canon["name"] = name

            # 1. Merge and deduplicate aliases safely
            ex_aliases = list(matched_canon.get("aliases") or [])
            for a in [name] + aliases:
                clean_a = clean_character_name(a)
                if clean_a and not is_blacklisted_name(clean_a) and clean_a.lower() != matched_canon["name"].lower():
                    if clean_a.lower() not in [x.lower() for x in ex_aliases]:
                        ex_aliases.append(clean_a)

            if alias_clusters:
                for k in [matched_canon["name"].lower(), name.lower()] + normalize_name_tokens(matched_canon["name"]) + normalize_name_tokens(name):
                    if k in alias_clusters:
                        for cl_name in alias_clusters[k]:
                            cl_clean = clean_character_name(cl_name)
                            if cl_clean and not is_blacklisted_name(cl_clean) and cl_clean.lower() != matched_canon["name"].lower():
                                if cl_clean.lower() not in [x.lower() for x in ex_aliases]:
                                    ex_aliases.append(cl_clean)

            matched_canon["aliases"] = sanitize_character_aliases(
                char_name=matched_canon["name"],
                aliases=ex_aliases,
                all_character_names=all_raw_names,
                alias_clusters=alias_clusters
            )

            # 2. Merge personality traits
            cur_traits = list(matched_canon.get("personality_traits") or [])
            for t in c.get("personality_traits") or []:
                if t and t not in cur_traits:
                    cur_traits.append(t)
            matched_canon["personality_traits"] = cur_traits

            # 3. Merge Backstory & Descriptions without overwriting
            c_desc = c.get("physical_description", "").strip()
            if c_desc:
                if not matched_canon.get("physical_description"):
                    matched_canon["physical_description"] = c_desc
                elif c_desc.lower() not in matched_canon["physical_description"].lower():
                    matched_canon["physical_description"] = f"{matched_canon['physical_description']}; {c_desc}"

            c_back = c.get("backstory", "").strip()
            if c_back:
                if not matched_canon.get("backstory"):
                    matched_canon["backstory"] = c_back
                elif c_back.lower() not in matched_canon["backstory"].lower():
                    matched_canon["backstory"] = f"{matched_canon['backstory']} {c_back}"

            # 4. Preserve portrait if missing on canonical
            if not matched_canon.get("portrait_url") and c.get("portrait_url"):
                matched_canon["portrait_url"] = c["portrait_url"]

            # 5. Merge Motivations, Goals, Fears, Secrets
            for field in ["motivations", "goals", "fears", "secrets"]:
                c_val = c.get(field, "").strip()
                if c_val:
                    if not matched_canon.get(field):
                        matched_canon[field] = c_val
                    elif c_val.lower() not in matched_canon[field].lower():
                        matched_canon[field] = f"{matched_canon[field]}; {c_val}"

            # 6. Merge Chapter Appearances & Evidence
            c_first = c.get("first_appearance")
            if c_first and not matched_canon.get("first_appearance"):
                matched_canon["first_appearance"] = c_first
            c_last = c.get("last_appearance")
            if c_last and not matched_canon.get("last_appearance"):
                matched_canon["last_appearance"] = c_last

            ex_apps = list(matched_canon.get("appearances") or [])
            for app_item in (c.get("appearances") or []):
                if app_item not in ex_apps:
                    ex_apps.append(app_item)
            matched_canon["appearances"] = ex_apps

            ex_ev = list(matched_canon.get("evidence") or [])
            for ev_item in (c.get("evidence") or []):
                if not any(x.get("chapter") == ev_item.get("chapter") for x in ex_ev):
                    ex_ev.append(ev_item)
            matched_canon["evidence"] = ex_ev

            # Preserve Person of Interest / Key Character designation
            if c.get("investigation_status") in ["person_of_interest", "culprit"] and matched_canon.get("investigation_status") == "unclassified":
                matched_canon["investigation_status"] = c["investigation_status"]

            # Update latest status if duplicate had newer appearance
            if c.get("status") and c.get("status") != "Unknown":
                matched_canon["status"] = c["status"]

            # 7. Merge Status History Provenance
            ex_hist = list(matched_canon.get("status_history") or [])
            ex_keys = {(h.get("chapter"), h.get("status", "").lower()) for h in ex_hist}
            for h in c.get("status_history") or []:
                k = (h.get("chapter"), h.get("status", "").lower())
                if k not in ex_keys:
                    ex_hist.append(h)
                    ex_keys.add(k)
            matched_canon["status_history"] = sorted(ex_hist, key=lambda x: x.get("chapter", 0))

            # 8. Merge Relationships recorded inside the character object
            ex_rels = list(matched_canon.get("relationships") or [])
            for r in c.get("relationships") or []:
                r_target = alias_to_canonical.get(r.get("target_id") or r.get("id"), r.get("target_id") or r.get("id"))
                r_target_name = r.get("target_name")
                if (r_target and r_target != matched_canon["id"]) or (r_target_name and r_target_name != matched_canon["name"]):
                    if not any(
                        (x.get("target_id") and x.get("target_id") == r_target) or
                        (x.get("target_name") and x.get("target_name") == r_target_name)
                        for x in ex_rels
                    ):
                        r_copy = dict(r)
                        if r_target:
                            r_copy["target_id"] = r_target
                        ex_rels.append(r_copy)
            matched_canon["relationships"] = ex_rels

        else:
            # Check if alias cluster has a fuller name for this standalone character
            if alias_clusters:
                c_clean_lower = c["name"].lower()
                if c_clean_lower in alias_clusters:
                    cluster_candidates = sorted(list(alias_clusters[c_clean_lower]), key=lambda x: (len(normalize_name_tokens(x)), len(x)), reverse=True)
                    if cluster_candidates:
                        fullest_in_cluster = clean_character_name(cluster_candidates[0])
                        if len(normalize_name_tokens(fullest_in_cluster)) > len(normalize_name_tokens(c["name"])):
                            old_name = c["name"]
                            c["name"] = fullest_in_cluster
                            if old_name.lower() not in [a.lower() for a in c.get("aliases", [])]:
                                c.setdefault("aliases", []).append(old_name)

                # Pull any cluster aliases into c["aliases"]
                c_aliases_pool = list(c.get("aliases") or [])
                for k in [c["name"].lower()] + normalize_name_tokens(c["name"]):
                    if k in alias_clusters:
                        for cl_name in alias_clusters[k]:
                            cl_clean = clean_character_name(cl_name)
                            if cl_clean and not is_blacklisted_name(cl_clean) and cl_clean.lower() != c["name"].lower():
                                if cl_clean.lower() not in [x.lower() for x in c_aliases_pool]:
                                    c_aliases_pool.append(cl_clean)
                c["aliases"] = sanitize_character_aliases(
                    char_name=c["name"],
                    aliases=c_aliases_pool,
                    all_character_names=all_raw_names,
                    alias_clusters=alias_clusters
                )

            canonical_list.append(c)
            alias_to_canonical[c["id"]] = c["id"]

    board_copy = dict(board)
    old_positions = board_copy.get("positions", {})
    new_positions = {}
    for cid, pos in old_positions.items():
        canon_id = alias_to_canonical.get(cid, cid)
        if canon_id in [c["id"] for c in canonical_list] and canon_id not in new_positions:
            new_positions[canon_id] = pos

    old_conns = board_copy.get("connections", [])
    new_conns = []
    seen_conn_keys = set()
    canon_ids = {c["id"] for c in canonical_list}
    for conn in old_conns:
        s_id = alias_to_canonical.get(conn.get("sourceId"), conn.get("sourceId"))
        t_id = alias_to_canonical.get(conn.get("targetId"), conn.get("targetId"))
        if s_id and t_id and s_id != t_id and s_id in canon_ids and t_id in canon_ids:
            direction = conn.get("direction", "bidirectional")
            r_type = conn.get("type", "allies")
            if direction == "directional":
                k = (s_id, t_id, r_type)
            else:
                k = tuple(sorted([s_id, t_id])) + (r_type,)
            if k not in seen_conn_keys:
                seen_conn_keys.add(k)
                conn_copy = dict(conn)
                conn_copy["sourceId"] = s_id
                conn_copy["targetId"] = t_id
                new_conns.append(conn_copy)

    board_copy["positions"] = new_positions
    board_copy["connections"] = new_conns
    return canonical_list, purged_ids, board_copy

@router.post("/api/stories/{story_id}/characters/deduplicate")
def deduplicate_story_characters(story_id: str):
    """
    Dossier Hygiene & Canonical Entity Consolidation:
    Identifies duplicate characters (e.g., 'Julian' vs 'Julian Calder', 'Lullu' vs 'Lullu Dickwala',
    'Saptarshi' vs 'Saptarshi Chowdhury', 'Dekh Saptarshi', conversational prefixes, nicknames)
    in the story's archive, merges their aliases, appearances, and traits into the canonical character,
    rewrites all board positions and connection IDs to the canonical ID, and purges redundant duplicate cards.
    Atomic and transaction-safe.
    """
    story = db_service.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chars = db_service.get_characters(story_id)
    if not chars:
        return {"canonical_count": 0, "purged_count": 0, "characters": []}

    chapters = db_service.get_chapters(story_id)
    full_text_parts = []
    for chap in chapters:
        c_text = chap.get("content", "")
        chap_pages = db_service.get_pages(chap.get("id", ""))
        if chap_pages:
            combined = " ".join([p.get("content", "") for p in chap_pages if p.get("content")])
            if len(combined) > len(c_text):
                c_text = combined
        clean = re.sub(r'<[^>]+>', ' ', c_text)
        clean = html.unescape(clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if clean:
            full_text_parts.append(clean)
    full_text = " ".join(full_text_parts)
    alias_clusters = extract_manuscript_alias_clusters(full_text)

    board = db_service.get_board(story_id) or {"story_id": story_id, "positions": {}, "connections": []}
    canonical_list, purged_ids, updated_board = deduplicate_character_entities_helper(chars, board, alias_clusters)

    # Batch consolidate atomically
    db_service.batch_consolidate_characters(
        story_id=story_id,
        canonical_chars=canonical_list,
        purged_ids=purged_ids,
        board_data=updated_board
    )

    all_current = db_service.get_characters(story_id)
    return {
        "success": True,
        "story_id": story_id,
        "canonical_count": len(all_current),
        "purged_count": len(purged_ids),
        "characters": all_current,
        "board": updated_board
    }

@router.post("/api/stories/{story_id}/board/auto-connect")
def auto_connect_story_board_relationships(story_id: str):
    """
    AI Story Relationship Analyzer & Auto-String Connector:
    Analyzes all chapters and characters in the story, determines authentic interpersonal
    dynamics and relationships, and automatically ties red threads / adjusts connections
    on the dossier board.
    """
    story = db_service.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # First, run deduplication to ensure connections attach strictly to canonical characters
    dedupe_res = deduplicate_story_characters(story_id)
    characters = dedupe_res["characters"]
    if len(characters) < 2:
        return {
            "success": False,
            "message": "At least 2 characters are required to analyze relationships.",
            "connections": []
        }

    char_id_map = {c["id"]: c for c in characters}

    # Fetch complete chapters and all associated pages from Writing Studio
    chapters = db_service.get_chapters(story_id)
    for c in chapters:
        cid = c.get("id")
        if cid:
            pages = db_service.get_pages(cid)
            if pages:
                non_empty = [p.get("content", "").strip() for p in pages if p.get("content") and p.get("content").strip() not in ["", "<p><br></p>"]]
                if non_empty:
                    c["content"] = "\n\n".join(non_empty)
                c["pages"] = pages

    events = db_service.get_events(story_id)
    existing_board = dedupe_res.get("board") or db_service.get_board(story_id) or {"story_id": story_id, "positions": {}, "connections": []}
    existing_conns = existing_board.get("connections", [])

    # Separate user-authored manual connections that must never be deleted
    manual_conns = []
    for c in existing_conns:
        s_id = c.get("sourceId") or c.get("source_id")
        t_id = c.get("targetId") or c.get("target_id")
        if s_id in char_id_map and t_id in char_id_map and s_id != t_id:
            c["sourceId"] = s_id
            c["targetId"] = t_id
            if not c.get("sourceName"):
                c["sourceName"] = char_id_map[s_id].get("name", "")
            if not c.get("targetName"):
                c["targetName"] = char_id_map[t_id].get("name", "")
            if c.get("is_manual") or c.get("user_edited"):
                manual_conns.append(c)

    # Run AI Relationship Analysis over the entire story canon and events with strict degree limits
    discovered_connections = ai_service.analyze_story_relationships_and_connections(
        characters=characters,
        chapters=chapters,
        story=story,
        events=events,
        existing_manual_conns=manual_conns
    )

    existing_board["connections"] = discovered_connections
    db_service.save_board(story_id, existing_board)

    # Synchronize into investigation board so corkboard threads accurately reflect the latest narrative relationships
    inv_board = db_service.get_investigation_board(story_id)
    if inv_board:
        from .plotholes import sync_investigation_board_relationships
        sync_investigation_board_relationships(story_id, inv_board)

    auto_added = len([c for c in discovered_connections if not (c.get("is_manual") or c.get("user_edited"))])
    return {
        "success": True,
        "story_id": story_id,
        "added_count": auto_added,
        "updated_count": len(discovered_connections) - auto_added,
        "total_connections": len(discovered_connections),
        "connections": discovered_connections
    }

@router.get("/api/stories/{story_id}/culprit")
def get_story_culprit(story_id: str):
    culprit = db_service.get_culprit(story_id)
    if not culprit:
        return {"story_id": story_id, "culprit_id": None}
    return culprit

@router.put("/api/stories/{story_id}/culprit")
def set_story_culprit(story_id: str, data: Dict[str, Any]):
    culprit_id = data.get("culprit_id")
    if culprit_id:
        char = db_service.get_character(culprit_id)
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
    return db_service.save_culprit(story_id, {"culprit_id": culprit_id})

@router.delete("/api/stories/{story_id}/culprit")
def remove_story_culprit(story_id: str):
    db_service.delete_culprit(story_id)
    return {"success": True, "story_id": story_id}
