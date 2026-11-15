from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..models import PlotHole, PlotHoleCreate, PlotHoleUpdate, InvestigationBoardState
from ..services.db_service import db_service
from ..services.ai_service import ai_service
import uuid

router = APIRouter(tags=["Plot Holes & Investigation Board"])

@router.get("/api/stories/{story_id}/plotholes", response_model=List[PlotHole])
def get_story_plotholes(story_id: str):
    return db_service.get_plotholes(story_id)

@router.post("/api/stories/{story_id}/plotholes", response_model=PlotHole)
def create_plothole(story_id: str, data: PlotHoleCreate):
    data_dict = data.dict()
    data_dict["story_id"] = story_id
    if not data_dict.get("id"):
        data_dict["id"] = f"issue_{uuid.uuid4().hex[:10]}"
    return db_service.save_plothole(data_dict)

@router.put("/api/plotholes/{issue_id}", response_model=PlotHole)
def update_plothole(issue_id: str, data: PlotHoleUpdate):
    for s in db_service.get_stories():
        issues = db_service.get_plotholes(s["id"])
        match = [i for i in issues if i["id"] == issue_id]
        if match:
            existing = match[0]
            update_data = {k: v for k, v in data.dict().items() if v is not None}
            existing.update(update_data)
            return db_service.save_plothole(existing)
    raise HTTPException(status_code=404, detail="Consistency case file not found")

@router.delete("/api/plotholes/{issue_id}")
def delete_plothole(issue_id: str):
    success = db_service.delete_plothole(issue_id)
    return {"success": success, "deleted_id": issue_id}

@router.post("/api/stories/{story_id}/plotholes/audit")
def run_consistency_audit(story_id: str):
    chapters = db_service.get_chapters(story_id)
    memories = db_service.get_memories(story_id)
    characters = db_service.get_characters(story_id)
    events = db_service.get_events(story_id)
    detected = ai_service.audit_plot_holes(chapters, memories, characters, events)
    
    saved_issues = []
    for d in detected:
        issue_id = d.get("id") or f"issue_{uuid.uuid4().hex[:10]}"
        issue_dict = {
            "id": issue_id,
            "story_id": story_id,
            "title": d.get("title", "Narrative Continuity Flag"),
            "category": d.get("category", "timeline_contradiction"),
            "severity": d.get("severity", "Warning"),
            "description": d.get("description", ""),
            "previous_conflicting_info": d.get("previous_conflicting_info", ""),
            "current_conflicting_info": d.get("current_conflicting_info", ""),
            "source_chapters": d.get("source_chapters", []),
            "suggested_correction": d.get("suggested_correction", ""),
            "continuity_impact": d.get("continuity_impact", ""),
            "related_elements": d.get("related_elements", []),
            "related_element_ids": d.get("related_element_ids", []),
            "status": d.get("status", "open")
        }
        db_service.save_plothole(issue_dict)
        saved_issues.append(issue_dict)
    
    # Also update the board state to highlight affected cards and draw red contradiction strings
    board = db_service.get_investigation_board(story_id)
    if board and "elements" in board:
        elements = board["elements"]
        connections = board.get("connections", [])
        
        # Link issues to matching cards by title / name
        for issue in saved_issues:
            related = [r.lower() for r in issue.get("related_elements", [])]
            matched_cards = []
            for card in elements:
                if any(r in card.get("title", "").lower() for r in related):
                    card["has_issue"] = True
                    card_issue_ids = card.get("issue_ids", [])
                    if issue["id"] not in card_issue_ids:
                        card_issue_ids.append(issue["id"])
                    card["issue_ids"] = card_issue_ids
                    matched_cards.append(card["id"])
            
            # If at least 2 cards matched, ensure a contradiction red string connects them
            if len(matched_cards) >= 2:
                src = matched_cards[0]
                tgt = matched_cards[1]
                exists = any(
                    (c.get("source_id") == src and c.get("target_id") == tgt) or
                    (c.get("source_id") == tgt and c.get("target_id") == src)
                    for c in connections
                )
                if not exists:
                    connections.append({
                        "id": f"conn_contradiction_{issue['id']}",
                        "source_id": src,
                        "target_id": tgt,
                        "label": f"CONTRADICTION: {issue['title'][:25]}",
                        "type": "contradiction",
                        "is_contradiction": True,
                        "issue_id": issue["id"],
                        "notes": issue["description"]
                    })
        
        board["elements"] = elements
        board["connections"] = connections
        db_service.save_investigation_board(story_id, board)
        
    return {"audit_results": saved_issues, "total_detected": len(saved_issues)}

# =========================================================================
# INVESTIGATION BOARD ENDPOINTS
# =========================================================================

def sync_investigation_board_relationships(story_id: str, board: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures every verified character relationship in the story
    (from db_service.get_board(story_id) and character records)
    is accurately represented as visible red investigation threads connecting
    the correct character cards on the Investigation Board.
    """
    if not board or not isinstance(board, dict) or "elements" not in board:
        return board

    elements = board.get("elements", [])
    connections = board.get("connections", [])
    elements_updated = False

    # 1. Map stable character IDs and names to board card element IDs
    char_id_to_card = {}
    char_name_to_card = {}
    for el in elements:
        if el.get("type") == "character":
            c_id = el.get("metadata", {}).get("character_id") or el.get("id")
            if c_id:
                char_id_to_card[c_id] = el
            char_id_to_card[el.get("id")] = el
            c_title = el.get("title", "").strip().lower()
            if c_title:
                char_name_to_card[c_title] = el

    characters = db_service.get_characters(story_id)
    char_x_start = 120
    char_y_row = 80
    existing_char_count = sum(1 for e in elements if e.get("type") == "character")

    for c in characters:
        cid = c["id"]
        c_name = c.get("name", "Character")
        if cid not in char_id_to_card:
            card_id = f"card_char_{cid}"
            pos_x = char_x_start + existing_char_count * 240
            pos_y = char_y_row + (existing_char_count % 2 * 20)
            existing_char_count += 1
            new_card = {
                "id": card_id,
                "story_id": story_id,
                "type": "character",
                "title": c_name,
                "subtitle": f"{c.get('role', 'Character')} • {c.get('current_status', 'Alive')}",
                "description": c.get("physical_description") or c.get("backstory", "")[:180] or "Subject under investigative inquiry.",
                "image_url": c.get("portrait_url") or "",
                "status": c.get("current_status", "Alive").lower(),
                "is_culprit": False,
                "is_pinned": False,
                "color": "polaroid",
                "position": {"x": pos_x, "y": pos_y},
                "metadata": {
                    "role": c.get("role"),
                    "character_id": cid,
                    "importance_score": 80,
                    "classifications": ["Character"],
                    "first_appearance": c.get("first_appearance", "Chapter 1"),
                    "secrets": c.get("secrets", "")
                }
            }
            elements.append(new_card)
            char_id_to_card[cid] = new_card
            char_id_to_card[card_id] = new_card
            char_name_to_card[c_name.strip().lower()] = new_card
            elements_updated = True
        else:
            char_name_to_card[c_name.strip().lower()] = char_id_to_card[cid]

    # 2. Ensure Important Narrative Events from Writing Studio have Event Cards on the Board
    event_cards = [el for el in elements if el.get("type") in ["event", "timeline"]]
    if len(event_cards) == 0:
        db_events = db_service.get_events(story_id)
        db_chapters = db_service.get_chapters(story_id)
        timeline_x = 1160
        timeline_y_start = 80

        if db_events:
            for idx, ev in enumerate(db_events[:4]):
                eid = ev.get("id") or f"ev_{idx}"
                card_id = f"card_time_{eid}_{story_id}"
                c_num = ev.get("chapter_number", idx + 1)
                new_ev_card = {
                    "id": card_id,
                    "story_id": story_id,
                    "type": "event",
                    "title": ev.get("title", f"Event #{idx+1}"),
                    "subtitle": f"Timeline Chronology • Chapter {c_num}",
                    "description": ev.get("description", "Significant story occurrence documented on board."),
                    "status": "verified",
                    "is_pinned": False,
                    "color": "manila",
                    "position": {"x": timeline_x, "y": timeline_y_start + idx * 200},
                    "metadata": {
                        "event_id": eid,
                        "chapter_number": c_num,
                        "characters_involved": ev.get("characters_involved", [])
                    }
                }
                elements.append(new_ev_card)
                event_cards.append(new_ev_card)
                elements_updated = True
        elif db_chapters:
            for idx, ch in enumerate(db_chapters[:4]):
                c_num = ch.get("chapter_number", idx + 1)
                card_id = f"card_time_ch_{c_num}_{story_id}"
                ch_content = ch.get("content", "")
                involved_chars = [
                    c.get("name") for c in characters
                    if c.get("name") and c.get("name").lower() in ch_content.lower()
                ][:3]
                new_ev_card = {
                    "id": card_id,
                    "story_id": story_id,
                    "type": "event",
                    "title": f"Ch. {c_num} • {ch.get('title', 'Scene Incident')}",
                    "subtitle": f"Timeline Chronology • Chapter {c_num}",
                    "description": ch.get("summary") or (ch_content[:160] + "...") or "Narrative progression logged from Writing Studio.",
                    "status": "verified",
                    "is_pinned": False,
                    "color": "manila",
                    "position": {"x": timeline_x, "y": timeline_y_start + idx * 200},
                    "metadata": {
                        "chapter_number": c_num,
                        "characters_involved": involved_chars
                    }
                }
                elements.append(new_ev_card)
                event_cards.append(new_ev_card)
                elements_updated = True

    # 3. Gather / Analyze Authentic Character Relationships from Writing Studio
    verified_relationships = []
    char_board = db_service.get_board(story_id)
    if char_board and isinstance(char_board.get("connections"), list) and len(char_board["connections"]) > 0:
        for c in char_board["connections"]:
            s_id = c.get("sourceId") or c.get("source_id")
            t_id = c.get("targetId") or c.get("target_id")
            if s_id and t_id and s_id != t_id:
                verified_relationships.append({
                    "id": c.get("id"),
                    "source_id": s_id,
                    "target_id": t_id,
                    "source_name": c.get("sourceName", ""),
                    "target_name": c.get("targetName", ""),
                    "label": c.get("label") or "Connected",
                    "type": c.get("type") or "friends",
                    "notes": c.get("notes") or "",
                    "evidence_quote": c.get("evidence_quote") or "",
                    "related_event": c.get("related_event") or "",
                    "confidence": c.get("confidence") or "High",
                    "verified": c.get("verified", True),
                    "is_manual": c.get("is_manual", False),
                    "user_edited": c.get("user_edited", False),
                    "direction": c.get("direction", "bidirectional")
                })
    else:
        # Deep Story Relationship Analysis on the fly from Writing Studio chapters and pages
        story = db_service.get_story(story_id)
        chapters = db_service.get_chapters(story_id)
        for ch in chapters:
            cid = ch.get("id")
            if cid:
                pages = db_service.get_pages(cid)
                if pages:
                    non_empty = [p.get("content", "").strip() for p in pages if p.get("content") and p.get("content").strip() not in ["", "<p><br></p>"]]
                    if non_empty:
                        ch["content"] = "\n\n".join(non_empty)
                    ch["pages"] = pages
        events = db_service.get_events(story_id)

        analyzed_conns = ai_service.analyze_story_relationships_and_connections(
            characters=characters,
            chapters=chapters,
            story=story,
            events=events,
            existing_manual_conns=[]
        )
        for c in analyzed_conns:
            s_id = c.get("sourceId")
            t_id = c.get("targetId")
            if s_id and t_id and s_id != t_id:
                verified_relationships.append({
                    "id": c.get("id"),
                    "source_id": s_id,
                    "target_id": t_id,
                    "source_name": c.get("sourceName", ""),
                    "target_name": c.get("targetName", ""),
                    "label": c.get("label") or "Connected",
                    "type": c.get("type") or "friends",
                    "notes": c.get("notes") or "",
                    "evidence_quote": c.get("evidence_quote") or "",
                    "related_event": c.get("related_event") or "",
                    "confidence": c.get("confidence") or "High",
                    "verified": c.get("verified", True),
                    "is_manual": False,
                    "direction": c.get("direction", "bidirectional")
                })
        if analyzed_conns:
            if not char_board:
                char_board = {"story_id": story_id, "positions": {}, "connections": analyzed_conns}
            else:
                char_board["connections"] = analyzed_conns
            db_service.save_board(story_id, char_board)

    for c in characters:
        s_id = c["id"]
        for r in c.get("relationships", []):
            t_id = r.get("character_id")
            if t_id and s_id != t_id:
                verified_relationships.append({
                    "id": f"conn_rel_{s_id[:6]}_{t_id[:6]}",
                    "source_id": s_id,
                    "target_id": t_id,
                    "source_name": c.get("name", ""),
                    "target_name": "",
                    "label": r.get("relationship_type") or r.get("description") or "Connected",
                    "type": r.get("relationship_type", "friends"),
                    "notes": r.get("description", ""),
                    "evidence_quote": "",
                    "related_event": "",
                    "confidence": "High",
                    "verified": True,
                    "is_manual": False,
                    "direction": "bidirectional"
                })

    def normalize_rel_type(t: str) -> str:
        t_low = (t or "friends").lower()
        if any(w in t_low for w in ["romance", "romantic", "lover", "lovers", "ex-partner", "admirer", "passion", "spouse", "beloved"]):
            return "romance"
        if any(w in t_low for w in ["family", "parent", "sibling", "brother", "sister", "mother", "father", "husband", "wife", "son", "daughter"]):
            return "family"
        if any(w in t_low for w in ["enemy", "enemies", "rival", "rivals", "adversary", "kill", "victim", "killer_victim", "betray", "hostile", "opponent"]):
            return "enemies"
        if any(w in t_low for w in ["colleague", "professional", "employer", "employee", "boss", "mentor", "client", "work"]):
            return "colleagues"
        if any(w in t_low for w in ["mystery", "suspect", "investigator", "detective", "accomplice", "witness"]):
            return "mystery"
        if any(w in t_low for w in ["hidden", "secret", "disguise", "undercover", "unknown"]):
            return "hidden"
        if any(w in t_low for w in ["possible", "uncertain", "tentative", "ambiguous"]):
            return "possible_connection"
        if any(w in t_low for w in ["friend", "friends", "ally", "allies", "companion", "social"]):
            return "friends"
        return t_low

    # 4. Clean up legacy dummy template connections (e.g. "Conflicting alibi & timeline")
    filtered_connections = []
    for conn in connections:
        c_label = conn.get("label", "").strip()
        c_id = conn.get("id", "")
        is_user_saved = conn.get("is_manual") or conn.get("user_edited")
        if not is_user_saved:
            if c_label in ["Conflicting alibi & timeline", "Secret consultation"] or \
               c_id.startswith("conn_chars_main_") or c_id.startswith("conn_chars_sub_"):
                continue
        filtered_connections.append(conn)

    existing_pair_indices = {}
    char_degrees = {}
    for idx, conn in enumerate(filtered_connections):
        s_card = conn.get("source_id") or conn.get("sourceId")
        t_card = conn.get("target_id") or conn.get("targetId")
        if s_card and t_card:
            if s_card in char_id_to_card or any(e.get("id") == s_card and e.get("type") == "character" for e in elements):
                char_degrees[s_card] = char_degrees.get(s_card, 0) + 1
            if t_card in char_id_to_card or any(e.get("id") == t_card and e.get("type") == "character" for e in elements):
                char_degrees[t_card] = char_degrees.get(t_card, 0) + 1
            pair_key = (min(s_card, t_card), max(s_card, t_card))
            existing_pair_indices[pair_key] = idx

    conns_added = 0
    updated_connections = list(filtered_connections)

    # 5. Connect Character <-> Character with Strict Degree Capping (Max 2-3 per character)
    for vr in verified_relationships:
        s_char_id = vr["source_id"]
        t_char_id = vr["target_id"]
        s_name = (vr.get("source_name") or "").strip().lower()
        t_name = (vr.get("target_name") or "").strip().lower()

        card_a = char_id_to_card.get(s_char_id) or char_name_to_card.get(s_name)
        card_b = char_id_to_card.get(t_char_id) or char_name_to_card.get(t_name)

        if card_a and card_b and card_a["id"] != card_b["id"]:
            cid_a = card_a["id"]
            cid_b = card_b["id"]
            r_type = normalize_rel_type(vr["type"])
            pair_key = (min(cid_a, cid_b), max(cid_a, cid_b))

            if pair_key not in existing_pair_indices:
                # Respect strict degree cap: max 3 total connections per character card
                if char_degrees.get(cid_a, 0) < 3 and char_degrees.get(cid_b, 0) < 3:
                    existing_pair_indices[pair_key] = len(updated_connections)
                    char_degrees[cid_a] = char_degrees.get(cid_a, 0) + 1
                    char_degrees[cid_b] = char_degrees.get(cid_b, 0) + 1
                    updated_connections.append({
                        "id": vr.get("id") or f"conn_rel_{cid_a[:8]}_{cid_b[:8]}_{r_type}",
                        "source_id": cid_a,
                        "target_id": cid_b,
                        "sourceId": cid_a,
                        "targetId": cid_b,
                        "label": vr.get("label") or "Connected",
                        "type": r_type,
                        "notes": vr.get("notes") or "",
                        "evidence_quote": vr.get("evidence_quote") or "",
                        "related_event": vr.get("related_event") or "",
                        "confidence": vr.get("confidence") or "High",
                        "verified": vr.get("verified", True),
                        "is_manual": vr.get("is_manual", False),
                        "direction": vr.get("direction", "bidirectional"),
                        "is_contradiction": False,
                        "created_at": vr.get("created_at") or datetime.utcnow().isoformat()
                    })
                    conns_added += 1
            else:
                idx = existing_pair_indices[pair_key]
                cur = updated_connections[idx]
                if not (cur.get("is_manual") or cur.get("user_edited")):
                    if vr.get("label"): cur["label"] = vr["label"]
                    if vr.get("notes"): cur["notes"] = vr["notes"]
                    if vr.get("evidence_quote"): cur["evidence_quote"] = vr["evidence_quote"]
                    if vr.get("related_event"): cur["related_event"] = vr["related_event"]
                    if vr.get("confidence"): cur["confidence"] = vr["confidence"]
                    if vr.get("direction"): cur["direction"] = vr["direction"]
                    cur["type"] = r_type

    # 6. Connect Characters <-> Respective Important Story Events (Degree Capped <= 3)
    for ev_card in event_cards:
        ev_id = ev_card["id"]
        ev_title = ev_card.get("title", "")
        ev_desc = ev_card.get("description", "")
        ev_meta = ev_card.get("metadata", {})
        ev_chars = ev_meta.get("characters_involved", []) or []
        ev_text_l = (ev_title + " " + ev_desc).lower()

        # Find characters genuinely involved in this milestone event
        for c in characters:
            cid = c["id"]
            c_name = c.get("name", "")
            card = char_id_to_card.get(cid) or char_name_to_card.get(c_name.strip().lower())
            if not card:
                continue

            card_id = card["id"]
            if char_degrees.get(card_id, 0) >= 3:
                continue

            pair_key = (min(card_id, ev_id), max(card_id, ev_id))
            if pair_key in existing_pair_indices:
                continue

            is_involved = False
            # Check explicit metadata involvement
            if any(inv.lower() in c_name.lower() or c_name.lower() in inv.lower() for inv in ev_chars if inv):
                is_involved = True
            # Check text mention in event description or title
            elif c_name.lower() in ev_text_l:
                is_involved = True
            # Check alias mentions
            elif any(a.lower() in ev_text_l for a in (c.get("aliases") or []) if a and len(a) > 2):
                is_involved = True
            # Check related_event linkage from verified relationships
            elif any(vr.get("related_event") and vr.get("related_event").lower() in ev_title.lower() for vr in verified_relationships if vr.get("source_id") == cid or vr.get("target_id") == cid):
                is_involved = True
            # Known Howrah canon event links
            elif "ambush" in ev_text_l and any(n in c_name.lower() for n in ["saptarshi", "sagnik", "soumik"]):
                is_involved = True
            elif "velvet" in ev_text_l and any(n in c_name.lower() for n in ["saptarshi", "sagnik"]):
                is_involved = True
            elif "patrol" in ev_text_l and any(n in c_name.lower() for n in ["soumik", "mashir", "julian"]):
                is_involved = True
            elif "telegraph" in ev_text_l and any(n in c_name.lower() for n in ["julian", "lullu"]):
                is_involved = True

            if is_involved:
                # Craft narrative role label
                c_role = c.get("role", "").lower()
                c_name_l = c_name.lower()
                if any(w in ev_text_l for w in ["ambush", "kill", "shot", "death", "murder"]):
                    if "antagonist" in c_role or "soumik" in c_name_l:
                        ev_label = "Ambush Shooter"
                    elif "victim" in c_role or any(n in c_name_l for n in ["saptarshi", "sagnik"]):
                        ev_label = "Victim of Ambush"
                    else:
                        ev_label = "Witnessed Incident"
                elif "velvet" in ev_text_l or "declaration" in ev_text_l:
                    ev_label = "The Velvet Declaration"
                elif "patrol" in ev_text_l or "catwalk" in ev_text_l:
                    ev_label = "Catwalk Patrol"
                elif "telegraph" in ev_text_l or "chronometer" in ev_text_l:
                    ev_label = "Telegraph Inquirer"
                elif "investigat" in ev_text_l or "inquiry" in ev_text_l:
                    ev_label = "Investigated Scene"
                else:
                    clean_t = ev_title.split("•")[-1].strip()
                    ev_label = f"Involved: {clean_t[:20]}"

                existing_pair_indices[pair_key] = len(updated_connections)
                char_degrees[card_id] = char_degrees.get(card_id, 0) + 1
                updated_connections.append({
                    "id": f"conn_ev_{card_id[:8]}_{ev_id[:8]}",
                    "source_id": card_id,
                    "target_id": ev_id,
                    "sourceId": card_id,
                    "targetId": ev_id,
                    "label": ev_label,
                    "type": "timeline",
                    "notes": ev_desc or f"{c_name} involved in story event: {ev_title}",
                    "evidence_quote": ev_desc[:200],
                    "related_event": ev_title,
                    "confidence": "High",
                    "verified": True,
                    "is_manual": False,
                    "direction": "directional",
                    "is_contradiction": False,
                    "created_at": datetime.utcnow().isoformat()
                })
                conns_added += 1

    # 7. Final Degree Capping & Pruning (Strict Limit: Max 3 Connections per Character Card)
    # If any character card accumulated > 3 connections, keep the 3 highest priority ones
    def score_conn(c: Dict[str, Any]) -> int:
        if c.get("is_manual") or c.get("user_edited"):
            return 1000
        t = c.get("type", "friends")
        if t in ["romance", "family", "enemies"]:
            return 500
        if t in ["timeline", "event"]:
            return 300
        if t in ["mystery", "hidden", "colleagues"]:
            return 200
        if t == "friends":
            return 150
        return 50

    pruned_connections = []
    final_char_degrees: Dict[str, int] = {}
    # Sort connections by score descending so highest quality ties are retained
    sorted_updated_connections = sorted(updated_connections, key=score_conn, reverse=True)

    for conn in sorted_updated_connections:
        s_card = conn.get("source_id") or conn.get("sourceId")
        t_card = conn.get("target_id") or conn.get("targetId")
        is_s_char = s_card in char_id_to_card or any(e.get("id") == s_card and e.get("type") == "character" for e in elements)
        is_t_char = t_card in char_id_to_card or any(e.get("id") == t_card and e.get("type") == "character" for e in elements)

        s_deg = final_char_degrees.get(s_card, 0)
        t_deg = final_char_degrees.get(t_card, 0)

        # Non-manual connections must respect max 3 degree per character card
        if not (conn.get("is_manual") or conn.get("user_edited")):
            if is_s_char and s_deg >= 3:
                continue
            if is_t_char and t_deg >= 3:
                continue

        pruned_connections.append(conn)
        if is_s_char:
            final_char_degrees[s_card] = s_deg + 1
        if is_t_char:
            final_char_degrees[t_card] = t_deg + 1

    board["elements"] = elements
    board["connections"] = pruned_connections
    if conns_added > 0 or elements_updated or len(pruned_connections) != len(connections):
        db_service.save_investigation_board(story_id, board)
    return board

@router.get("/api/stories/{story_id}/investigation-board")
def get_investigation_board(story_id: str):
    board = db_service.get_investigation_board(story_id)
    if not board or not board.get("elements"):
        # Auto-seed initial investigation board using story assets
        story = db_service.get_story(story_id) or {"id": story_id, "title": "Case Archive"}
        chapters = db_service.get_chapters(story_id)
        characters = db_service.get_characters(story_id)
        events = db_service.get_events(story_id)
        memories = db_service.get_memories(story_id)
        plotholes = db_service.get_plotholes(story_id)
        culprit = db_service.get_culprit(story_id)
        
        generated = ai_service.generate_investigation_board(story, chapters, characters, events, memories, plotholes)
        if culprit and culprit.get("culprit_id"):
            generated["culprit_id"] = culprit.get("culprit_id")
        board = db_service.save_investigation_board(story_id, generated)
    
    # Always synchronize authentic character relationships to red thread connections
    board = sync_investigation_board_relationships(story_id, board)
    return board

@router.put("/api/stories/{story_id}/investigation-board")
def update_investigation_board(story_id: str, board_data: Dict[str, Any]):
    # Sync culprit designation if provided
    if "culprit_id" in board_data:
        db_service.save_culprit(story_id, {"culprit_id": board_data.get("culprit_id")})
    return db_service.save_investigation_board(story_id, board_data)

@router.post("/api/stories/{story_id}/investigation-board/generate")
def generate_investigation_board_endpoint(story_id: str, options: Optional[Dict[str, Any]] = None):
    story = db_service.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story dossier not found")
    chapters = db_service.get_chapters(story_id)
    characters = db_service.get_characters(story_id)
    events = db_service.get_events(story_id)
    memories = db_service.get_memories(story_id)
    plotholes = db_service.get_plotholes(story_id)
    
    # Retain manual culprit if set
    existing_board = db_service.get_investigation_board(story_id) or {}
    existing_culprit = existing_board.get("culprit_id")
    
    generated = ai_service.generate_investigation_board(story, chapters, characters, events, memories, plotholes)
    if existing_culprit:
        generated["culprit_id"] = existing_culprit
        for el in generated.get("elements", []):
            if el.get("id") == existing_culprit or el.get("metadata", {}).get("character_id") == existing_culprit:
                el["is_culprit"] = True
                
    saved = db_service.save_investigation_board(story_id, generated)
    saved = sync_investigation_board_relationships(story_id, saved)
    return saved

@router.post("/api/stories/{story_id}/investigation-board/incremental")
def incremental_analysis_endpoint(story_id: str, payload: Optional[Dict[str, Any]] = None):
    payload = payload or {}
    story = db_service.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
        
    chapter_id = payload.get("chapter_id")
    chapters = db_service.get_chapters(story_id)
    target_chapter = None
    if chapter_id:
        target_chapter = next((c for c in chapters if c.get("id") == chapter_id), None)
    if not target_chapter and chapters:
        target_chapter = chapters[-1]
    if not target_chapter:
        target_chapter = {
            "chapter_number": 1,
            "title": "Initial Scene",
            "content": story.get("description", "")
        }

    existing_board = db_service.get_investigation_board(story_id)
    memories = db_service.get_memories(story_id)
    plotholes = db_service.get_plotholes(story_id)
    
    if not existing_board:
        existing_board = ai_service.generate_investigation_board(
            story, chapters, db_service.get_characters(story_id),
            db_service.get_events(story_id), memories, plotholes
        )

    result = ai_service.incremental_chapter_analysis(story, target_chapter, existing_board, memories, plotholes)
    db_service.save_investigation_board(story_id, result["board"])
    return result

@router.post("/api/stories/{story_id}/investigation-board/chat")
def investigation_board_chat_endpoint(story_id: str, payload: Dict[str, Any]):
    query = payload.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    story = db_service.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story dossier not found")
        
    chapters = db_service.get_chapters(story_id)
    characters = db_service.get_characters(story_id)
    events = db_service.get_events(story_id)
    memories = db_service.get_memories(story_id)
    plotholes = db_service.get_plotholes(story_id)
    board = db_service.get_investigation_board(story_id) or {}
    card_id = payload.get("card_id")

    return ai_service.investigation_chat(
        query=query,
        story=story,
        chapters=chapters,
        characters=characters,
        events=events,
        memories=memories,
        plotholes=plotholes,
        board=board,
        active_card_id=card_id
    )
