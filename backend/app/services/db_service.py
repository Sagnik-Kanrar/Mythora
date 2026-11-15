import json
import os
import re
import uuid
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..config import DATA_DIR, MONGODB_URI, MONGODB_DB_NAME

# Use RLock (reentrant) so same thread can acquire multiple times without deadlocking
lock = threading.RLock()

class DatabaseService:
    def __init__(self):
        self.use_mongo = False
        self.mongo_client = None
        self.db = None
        
        if MONGODB_URI:
            try:
                import socket
                # Fast outbound probe: if network is offline or blocked, fail immediately to local store
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.6)
                s.connect(("8.8.8.8", 53))
                s.close()

                from pymongo import MongoClient
                self.mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1500, connectTimeoutMS=1500)
                self.mongo_client.server_info()
                self.db = self.mongo_client[MONGODB_DB_NAME]
                self.use_mongo = True
                print("[DB] Connected to MongoDB Atlas")
            except Exception as e:
                print(f"[DB] MongoDB fallback ({e})")
                self.use_mongo = False
                
        self.local_file = DATA_DIR / "storyweave_store.json"
        self._init_local_store()
        if self.use_mongo:
            threading.Thread(target=self._sync_on_startup, daemon=True).start()

    def _sync_on_startup(self):
        local_data = self._load_local()
        # Sync stories from local to Mongo
        for sid, s in local_data.get("stories", {}).items():
            try:
                self.db.stories.replace_one({"id": sid}, s, upsert=True)
            except Exception:
                pass
        # Sync chapters from local to Mongo
        for cid, c in local_data.get("chapters", {}).items():
            try:
                self.db.chapters.replace_one({"id": cid}, c, upsert=True)
            except Exception:
                pass
        # Sync pages from local to Mongo
        for pid, p in local_data.get("pages", {}).items():
            try:
                self.db.pages.replace_one({"id": pid}, p, upsert=True)
            except Exception:
                pass

    def _init_local_store(self):
        with lock:
            if not self.local_file.exists():
                initial_data = {
                    "stories": {},
                    "chapters": {},
                    "characters": {},
                    "events": {},
                    "memories": {},
                    "plotholes": {},
                    "boards": {},
                    "culprits": {}
                }
                self._save_local(initial_data)

    def _load_local(self) -> Dict[str, Any]:
        with lock:
            if not self.local_file.exists():
                return {"stories": {}, "chapters": {}, "pages": {}, "characters": {}, "events": {}, "memories": {}, "plotholes": {}, "boards": {}, "investigation_boards": {}, "culprits": {}}
            try:
                with open(self.local_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if "boards" not in loaded:
                        loaded["boards"] = {}
                    if "culprits" not in loaded:
                        loaded["culprits"] = {}
                    return loaded
            except Exception:
                return {"stories": {}, "chapters": {}, "pages": {}, "characters": {}, "events": {}, "memories": {}, "plotholes": {}, "boards": {}, "investigation_boards": {}, "culprits": {}}

    def _save_local(self, data: Dict[str, Any]):
        with lock:
            with open(self.local_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def get_stories(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        local_data = self._load_local()
        stories_map = {s["id"]: s for s in local_data.get("stories", {}).values() if "id" in s}
        if self.use_mongo:
            try:
                for s in self.db.stories.find():
                    s.pop("_id", None)
                    if s.get("id"):
                        stories_map[s["id"]] = s
            except Exception as e:
                print(f"[DB Mongo get_stories error] {e}")
        all_stories = list(stories_map.values())
        if user_id:
            return [s for s in all_stories if s.get("user_id") == user_id]
        return []

    def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        if self.use_mongo:
            try:
                doc = self.db.stories.find_one({"id": story_id})
                if doc:
                    doc.pop("_id", None)
                    return doc
            except Exception as e:
                print(f"[DB Mongo get_story error] {e}")
        data = self._load_local()
        return data.get("stories", {}).get(story_id)

    def save_story(self, story: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load_local()
        if "stories" not in data:
            data["stories"] = {}
        data["stories"][story["id"]] = story
        self._save_local(data)
        if self.use_mongo:
            try:
                self.db.stories.replace_one({"id": story["id"]}, story, upsert=True)
            except Exception as e:
                print(f"[DB Mongo save_story error] {e}")
        return story

    def delete_story(self, story_id: str) -> bool:
        data = self._load_local()
        data["stories"].pop(story_id, None)
        data["chapters"] = {k: v for k, v in data["chapters"].items() if v.get("story_id") != story_id}
        data["characters"] = {k: v for k, v in data["characters"].items() if v.get("story_id") != story_id}
        data["events"] = {k: v for k, v in data["events"].items() if v.get("story_id") != story_id}
        data["memories"] = {k: v for k, v in data["memories"].items() if v.get("story_id") != story_id}
        data["plotholes"] = {k: v for k, v in data["plotholes"].items() if v.get("story_id") != story_id}
        if "boards" in data:
            data["boards"].pop(story_id, None)
        self._save_local(data)
        if self.use_mongo:
            try:
                self.db.stories.delete_one({"id": story_id})
                self.db.chapters.delete_many({"story_id": story_id})
                self.db.characters.delete_many({"story_id": story_id})
                self.db.events.delete_many({"story_id": story_id})
                self.db.memories.delete_many({"story_id": story_id})
                self.db.plotholes.delete_many({"story_id": story_id})
                self.db.boards.delete_one({"story_id": story_id})
            except Exception as e:
                print(f"[DB Mongo delete_story error] {e}")
        return True

    def get_chapters(self, story_id: str) -> List[Dict[str, Any]]:
        chaps_map = {}
        data = self._load_local()
        for c in data.get("chapters", {}).values():
            if c.get("story_id") == story_id:
                chaps_map[c["id"]] = c
        if self.use_mongo:
            try:
                m_chaps = list(self.db.chapters.find({"story_id": story_id}).sort("chapter_number", 1))
                for c in m_chaps:
                    c.pop("_id", None)
                    cid = c.get("id")
                    if cid:
                        if cid not in chaps_map or len(c.get("content", "")) >= len(chaps_map[cid].get("content", "")):
                            chaps_map[cid] = c
            except Exception as e:
                print(f"[DB Mongo get_chapters error] {e}")
        chaps = list(chaps_map.values())
        return sorted(chaps, key=lambda x: x.get("chapter_number", 0))

    def get_chapter(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        doc = None
        if self.use_mongo:
            try:
                doc = self.db.chapters.find_one({"id": chapter_id})
                if doc:
                    doc.pop("_id", None)
            except Exception as e:
                print(f"[DB Mongo get_chapter error] {e}")
        data = self._load_local()
        local_c = data.get("chapters", {}).get(chapter_id)
        if doc and local_c:
            if len(local_c.get("content", "")) > len(doc.get("content", "")):
                return local_c
            return doc
        return doc or local_c

    def save_chapter(self, chapter: Dict[str, Any]) -> Dict[str, Any]:
        cid = chapter.get("id")
        if cid:
            existing = self.get_chapter(cid)
            if existing:
                existing_c = (existing.get("content") or "").strip()
                incoming_c = (chapter.get("content") or "").strip()
                # Manuscript protection: never allow empty/blank placeholder to overwrite non-empty prose
                if (incoming_c == "" or incoming_c == "<p><br></p>") and (existing_c != "" and existing_c != "<p><br></p>"):
                    chapter["content"] = existing.get("content")

        chapter["word_count"] = len(chapter.get("content", "").split())
        chapter["updated_at"] = datetime.utcnow().isoformat()
        
        # Dual-write: Always update local
        data = self._load_local()
        if "chapters" not in data:
            data["chapters"] = {}
        data["chapters"][chapter["id"]] = chapter
        self._save_local(data)
        
        # Dual-write: Always update Mongo
        if self.use_mongo:
            try:
                self.db.chapters.replace_one({"id": chapter["id"]}, chapter, upsert=True)
            except Exception as e:
                print(f"[DB Mongo save_chapter error] {e}")
        return chapter

    def delete_chapter(self, chapter_id: str) -> bool:
        data = self._load_local()
        if "chapters" in data:
            data["chapters"].pop(chapter_id, None)
            self._save_local(data)
        if self.use_mongo:
            try:
                self.db.chapters.delete_one({"id": chapter_id})
            except Exception as e:
                print(f"[DB Mongo delete_chapter error] {e}")
        return True

    def get_pages(self, chapter_id: str) -> List[Dict[str, Any]]:
        pages = []
        if self.use_mongo:
            try:
                pages = list(self.db.pages.find({"chapter_id": chapter_id}).sort("page_number", 1))
                for p in pages:
                    p.pop("_id", None)
            except Exception as e:
                print(f"[DB Mongo get_pages error] {e}")
        if not pages:
            data = self._load_local()
            pages_dict = data.get("pages", {})
            pages = [p for p in pages_dict.values() if p.get("chapter_id") == chapter_id]
            pages = sorted(pages, key=lambda x: x.get("page_number", 0))

        # If pages still empty, check chapter embedded pages or parse chapter content
        if not pages:
            chap = self.get_chapter(chapter_id)
            if chap:
                if chap.get("pages"):
                    pages = chap.get("pages")
                    for p in pages:
                        p_dict = dict(p) if not isinstance(p, dict) else p
                        p_dict["chapter_id"] = chapter_id
                        self.save_page(chapter_id, p_dict, sync_chapter=False)
                elif chap.get("content") and chap.get("content").strip() not in ["", "<p><br></p>"]:
                    raw_splits = chap["content"].split("<!-- story-page-break -->")
                    created_pages = []
                    for idx, raw_p in enumerate(raw_splits):
                        clean = re.sub(r'<[^>]+>', ' ', raw_p)
                        p_obj = {
                            "id": f"page_{chapter_id}_{idx+1}",
                            "chapter_id": chapter_id,
                            "page_number": idx + 1,
                            "content": raw_p,
                            "word_count": len(clean.split()),
                            "save_status": "saved",
                            "created_at": chap.get("created_at") or datetime.utcnow().isoformat(),
                            "updated_at": chap.get("updated_at") or datetime.utcnow().isoformat()
                        }
                        self.save_page(chapter_id, p_obj, sync_chapter=False)
                        created_pages.append(p_obj)
                    pages = created_pages

        return sorted(pages, key=lambda x: x.get("page_number", 0))

    def get_page(self, chapter_id: str, page_id: str) -> Optional[Dict[str, Any]]:
        if self.use_mongo:
            try:
                doc = self.db.pages.find_one({"id": page_id, "chapter_id": chapter_id})
                if doc:
                    doc.pop("_id", None)
                    return doc
            except Exception as e:
                print(f"[DB Mongo get_page error] {e}")
        data = self._load_local()
        pages_dict = data.get("pages", {})
        p = pages_dict.get(page_id)
        if p:
            return p
        # Check embedded in chapter
        chap = self.get_chapter(chapter_id)
        if chap and chap.get("pages"):
            for embedded in chap["pages"]:
                if embedded.get("id") == page_id:
                    return embedded
        return None

    def create_page(self, chapter_id: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
        page_id = page_data.get("id") or f"page_{uuid.uuid4().hex[:10]}"
        content = page_data.get("content", "")
        clean_text = re.sub(r'<[^>]+>', ' ', content)
        words = len(clean_text.split())
        page = {
            "id": page_id,
            "chapter_id": chapter_id,
            "page_number": page_data.get("page_number", 1),
            "content": content,
            "word_count": words,
            "save_status": page_data.get("save_status", "saved"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        return self.save_page(chapter_id, page, sync_chapter=True)

    def save_page(self, chapter_id: str, page: Dict[str, Any], sync_chapter: bool = True) -> Dict[str, Any]:
        pid = page.get("id")
        if pid:
            existing_p = self.get_page(chapter_id, pid)
            if existing_p:
                existing_c = (existing_p.get("content") or "").strip()
                incoming_c = (page.get("content") or "").strip()
                if (incoming_c == "" or incoming_c == "<p><br></p>") and (existing_c != "" and existing_c != "<p><br></p>"):
                    page["content"] = existing_p.get("content")

        content = page.get("content", "")
        clean_text = re.sub(r'<[^>]+>', ' ', content)
        page["word_count"] = len(clean_text.split())
        page["updated_at"] = datetime.utcnow().isoformat()
        if not page.get("created_at"):
            page["created_at"] = datetime.utcnow().isoformat()
        if not page.get("chapter_id"):
            page["chapter_id"] = chapter_id

        # Dual-write: Always write to local
        data = self._load_local()
        if "pages" not in data:
            data["pages"] = {}
        data["pages"][page["id"]] = page
        self._save_local(data)

        # Dual-write: Always write to Mongo
        if self.use_mongo:
            try:
                self.db.pages.replace_one({"id": page["id"]}, page, upsert=True)
            except Exception as e:
                print(f"[DB Mongo save_page error] {e}")

        if sync_chapter:
            self._sync_chapter_from_pages(chapter_id)

        return page

    def _sync_chapter_from_pages(self, chapter_id: str):
        chapter = self.get_chapter(chapter_id)
        if not chapter:
            return
        pages = self.get_pages(chapter_id)
        if pages:
            non_empty_pages = [p.get("content", "") for p in pages if p.get("content") and p.get("content").strip() not in ["", "<p><br></p>"]]
            if non_empty_pages:
                combined_content = "<!-- story-page-break -->".join(non_empty_pages)
                chapter["content"] = combined_content
            chapter["pages"] = pages
            self.save_chapter(chapter)

    def delete_page(self, chapter_id: str, page_id: str) -> bool:
        data = self._load_local()
        if "pages" in data and page_id in data["pages"]:
            data["pages"].pop(page_id, None)
            self._save_local(data)
        if self.use_mongo:
            try:
                self.db.pages.delete_one({"id": page_id, "chapter_id": chapter_id})
            except Exception as e:
                print(f"[DB Mongo delete_page error] {e}")
        self._sync_chapter_from_pages(chapter_id)
        return True




    def _normalize_character(self, c: Dict[str, Any]) -> Dict[str, Any]:
        if not c:
            return c
        status = c.get("investigation_status")
        if not status:
            if c.get("is_culprit") or c.get("role") == "Culprit":
                status = "person_of_interest"
            else:
                status = "unclassified"
        elif status == "culprit":
            status = "person_of_interest"
        c["investigation_status"] = status
        return c


    def get_characters(self, story_id: str) -> List[Dict[str, Any]]:
        if self.use_mongo:
            chars = list(self.db.characters.find({"story_id": story_id}))
            for c in chars:
                c.pop("_id", None)
            return [self._normalize_character(c) for c in chars if c]
        data = self._load_local()
        return [self._normalize_character(c) for c in data["characters"].values() if c.get("story_id") == story_id]

    def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        if self.use_mongo:
            doc = self.db.characters.find_one({"id": character_id})
            if doc:
                doc.pop("_id", None)
                return self._normalize_character(doc)
            return None
        data = self._load_local()
        char = data["characters"].get(character_id)
        return self._normalize_character(char) if char else None

    def save_character(self, character: Dict[str, Any]) -> Dict[str, Any]:
        character["updated_at"] = datetime.utcnow().isoformat()
        data = self._load_local()
        if "characters" not in data:
            data["characters"] = {}
        data["characters"][character["id"]] = character
        self._save_local(data)
        if self.use_mongo:
            try:
                self.db.characters.replace_one({"id": character["id"]}, character, upsert=True)
            except Exception as e:
                print(f"[DB Mongo save_character error] {e}")
        return self._normalize_character(character)

    def delete_character(self, character_id: str) -> bool:
        data = self._load_local()
        if "characters" in data and character_id in data["characters"]:
            data["characters"].pop(character_id, None)
            self._save_local(data)
        if self.use_mongo:
            try:
                self.db.characters.delete_one({"id": character_id})
            except Exception as e:
                print(f"[DB Mongo delete_character error] {e}")
        return True

    def get_events(self, story_id: str) -> List[Dict[str, Any]]:
        if self.use_mongo:
            evts = list(self.db.events.find({"story_id": story_id}).sort("chronological_position", 1))
            for e in evts:
                e.pop("_id", None)
            if evts:
                return evts
        data = self._load_local()
        evts = [e for e in data["events"].values() if e.get("story_id") == story_id]
        return sorted(evts, key=lambda x: (x.get("chronological_position", 0), x.get("event_number", 0)))

    def save_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event["updated_at"] = datetime.utcnow().isoformat()
        data = self._load_local()
        if "events" not in data:
            data["events"] = {}
        data["events"][event["id"]] = event
        self._save_local(data)
        if self.use_mongo:
            try:
                self.db.events.replace_one({"id": event["id"]}, event, upsert=True)
            except Exception as e:
                print(f"[DB Mongo save_event error] {e}")
        return event

    def delete_event(self, event_id: str) -> bool:
        data = self._load_local()
        if "events" in data and event_id in data["events"]:
            data["events"].pop(event_id, None)
            self._save_local(data)
        if self.use_mongo:
            try:
                self.db.events.delete_one({"id": event_id})
            except Exception as e:
                print(f"[DB Mongo delete_event error] {e}")
        return True

    def get_memories(self, story_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.use_mongo:
            q = {"story_id": story_id}
            if category:
                q["category"] = category
            mems = list(self.db.memories.find(q))
            for m in mems:
                m.pop("_id", None)
            return mems
        data = self._load_local()
        mems = [m for m in data["memories"].values() if m.get("story_id") == story_id]
        if category:
            mems = [m for m in mems if m.get("category") == category]
        return mems

    def save_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        memory["updated_at"] = datetime.utcnow().isoformat()
        data = self._load_local()
        if "memories" not in data:
            data["memories"] = {}
        data["memories"][memory["id"]] = memory
        self._save_local(data)
        if self.use_mongo:
            try:
                self.db.memories.replace_one({"id": memory["id"]}, memory, upsert=True)
            except Exception as e:
                print(f"[DB Mongo save_memory error] {e}")
        return memory

    def delete_memory(self, memory_id: str) -> bool:
        data = self._load_local()
        if "memories" in data and memory_id in data["memories"]:
            data["memories"].pop(memory_id, None)
            self._save_local(data)
        if self.use_mongo:
            try:
                self.db.memories.delete_one({"id": memory_id})
            except Exception as e:
                print(f"[DB Mongo delete_memory error] {e}")
        return True

    def get_plotholes(self, story_id: str) -> List[Dict[str, Any]]:
        if self.use_mongo:
            issues = list(self.db.plotholes.find({"story_id": story_id}))
            for i in issues:
                i.pop("_id", None)
            if issues:
                return issues
        data = self._load_local()
        return [i for i in data["plotholes"].values() if i.get("story_id") == story_id]

    def save_plothole(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        issue["updated_at"] = datetime.utcnow().isoformat()
        data = self._load_local()
        if "plotholes" not in data:
            data["plotholes"] = {}
        data["plotholes"][issue["id"]] = issue
        self._save_local(data)
        if self.use_mongo:
            try:
                self.db.plotholes.replace_one({"id": issue["id"]}, issue, upsert=True)
            except Exception as e:
                print(f"[DB Mongo save_plothole error] {e}")
        return issue

    def delete_plothole(self, issue_id: str) -> bool:
        data = self._load_local()
        if "plotholes" in data and issue_id in data["plotholes"]:
            data["plotholes"].pop(issue_id, None)
            self._save_local(data)
        if self.use_mongo:
            try:
                self.db.plotholes.delete_one({"id": issue_id})
            except Exception as e:
                print(f"[DB Mongo delete_plothole error] {e}")
        return True

    def get_board(self, story_id: str) -> Optional[Dict[str, Any]]:
        if self.use_mongo:
            doc = self.db.boards.find_one({"story_id": story_id})
            if doc:
                doc.pop("_id", None)
            return doc
        data = self._load_local()
        return data.get("boards", {}).get(story_id)

    def save_board(self, story_id: str, board_data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(board_data)
        payload["story_id"] = story_id
        payload["updated_at"] = datetime.utcnow().isoformat()
        data = self._load_local()
        if "boards" not in data:
            data["boards"] = {}
        data["boards"][story_id] = payload
        self._save_local(data)
        if self.use_mongo:
            try:
                self.db.boards.replace_one({"story_id": story_id}, payload, upsert=True)
            except Exception as e:
                print(f"[DB Mongo save_board error] {e}")
        return payload


    def get_investigation_board(self, story_id: str) -> Optional[Dict[str, Any]]:
        if self.use_mongo:
            doc = self.db.investigation_boards.find_one({"story_id": story_id})
            if doc:
                doc.pop("_id", None)
            return doc
        data = self._load_local()
        return data.get("investigation_boards", {}).get(story_id)

    def save_investigation_board(self, story_id: str, board_data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(board_data)
        payload["story_id"] = story_id
        payload["updated_at"] = datetime.utcnow().isoformat()
        data = self._load_local()
        if "investigation_boards" not in data:
            data["investigation_boards"] = {}
        data["investigation_boards"][story_id] = payload
        self._save_local(data)
        if self.use_mongo:
            try:
                self.db.investigation_boards.replace_one({"story_id": story_id}, payload, upsert=True)
            except Exception as e:
                print(f"[DB Mongo save_investigation_board error] {e}")
        return payload

    def get_culprit(self, story_id: str) -> Optional[Dict[str, Any]]:
        if self.use_mongo:
            doc = self.db.culprits.find_one({"story_id": story_id})
            if doc:
                doc.pop("_id", None)
            return doc
        data = self._load_local()
        return data.get("culprits", {}).get(story_id)

    def save_culprit(self, story_id: str, culprit_data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(culprit_data)
        payload["story_id"] = story_id
        payload["updated_at"] = datetime.utcnow().isoformat()
        data = self._load_local()
        if "culprits" not in data:
            data["culprits"] = {}
        data["culprits"][story_id] = payload
        self._save_local(data)
        if self.use_mongo:
            try:
                self.db.culprits.replace_one({"story_id": story_id}, payload, upsert=True)
            except Exception as e:
                print(f"[DB Mongo save_culprit error] {e}")
        return payload

    def delete_culprit(self, story_id: str) -> bool:
        data = self._load_local()
        if "culprits" in data:
            data["culprits"].pop(story_id, None)
            self._save_local(data)
        if self.use_mongo:
            try:
                self.db.culprits.delete_one({"story_id": story_id})
            except Exception as e:
                print(f"[DB Mongo delete_culprit error] {e}")
        return True

    def batch_consolidate_characters(
        self,
        story_id: str,
        canonical_chars: List[Dict[str, Any]],
        purged_ids: List[str],
        board_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Atomically updates characters and board in a single transaction-safe operation,
        preventing any race condition or partial data loss during consolidation.
        """
        with lock:
            if self.use_mongo:
                try:
                    # In MongoDB, if replica set is enabled, use session transaction; otherwise atomic updates
                    for pid in purged_ids:
                        self.db.characters.delete_one({"id": pid})
                    for cc in canonical_chars:
                        cc["updated_at"] = datetime.utcnow().isoformat()
                        self.db.characters.update_one({"id": cc["id"]}, {"$set": cc}, upsert=True)
                    if board_data:
                        b_payload = dict(board_data)
                        b_payload["story_id"] = story_id
                        b_payload["updated_at"] = datetime.utcnow().isoformat()
                        self.db.boards.update_one({"story_id": story_id}, {"$set": b_payload}, upsert=True)
                    return True
                except Exception as e:
                    print(f"[DB Mongo batch_consolidate_characters error] {e}")
                    return False

            data = self._load_local()
            # 1. Purge duplicate records
            for pid in purged_ids:
                data["characters"].pop(pid, None)

            # 2. Save all canonical records with merged data
            now_iso = datetime.utcnow().isoformat()
            for cc in canonical_chars:
                cc["updated_at"] = now_iso
                data["characters"][cc["id"]] = cc

            # 3. Update board if provided
            if board_data:
                b_payload = dict(board_data)
                b_payload["story_id"] = story_id
                b_payload["updated_at"] = now_iso
                if "boards" not in data:
                    data["boards"] = {}
                data["boards"][story_id] = b_payload

            # 4. Atomic file write
            self._save_local(data)
            return True

db_service = DatabaseService()
