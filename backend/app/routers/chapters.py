from fastapi import APIRouter, HTTPException
from typing import List
from ..models import Chapter, ChapterCreate, ChapterUpdate, Page, PageCreate, PageUpdate
from ..services.db_service import db_service
from ..services.ai_service import ai_service
from ..services.vector_service import vector_service
import uuid

router = APIRouter(tags=["Chapters"])

@router.get("/api/stories/{story_id}/chapters", response_model=List[Chapter])
def get_story_chapters(story_id: str):
    return db_service.get_chapters(story_id)

@router.post("/api/stories/{story_id}/chapters", response_model=Chapter)
@router.post("/api/chapters", response_model=Chapter)
def create_chapter(data: ChapterCreate, story_id: str = None):
    data_dict = data.dict()
    sid = story_id or data_dict.get("story_id") or data_dict.get("storyId")
    if not sid:
        raise HTTPException(status_code=400, detail="story_id is required")
    data_dict["story_id"] = sid
    if not data_dict.get("chapter_number"):
        data_dict["chapter_number"] = data_dict.get("order") or 1
    # Ensure title is trimmed and has valid fallback if empty
    title = (data_dict.get("title") or "").strip()
    if not title:
        title = f"Chapter {data_dict.get('chapter_number', 1)} - The Unfolding Incident"
    data_dict["title"] = title
    data_dict["id"] = f"chap_{uuid.uuid4().hex[:10]}"
    saved = db_service.save_chapter(data_dict)
    # Immediately index new chapter into ChromaDB semantic store
    try:
        vector_service.index_chapter(sid, saved)
    except Exception as e:
        print(f"[Chapter Indexing Error] {e}")
    return saved

@router.get("/api/chapters/{chapter_id}", response_model=Chapter)
def get_chapter(chapter_id: str):
    chap = db_service.get_chapter(chapter_id)
    if not chap:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chap

@router.put("/api/chapters/{chapter_id}", response_model=Chapter)
def update_chapter(chapter_id: str, data: ChapterUpdate):
    existing = db_service.get_chapter(chapter_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Chapter not found")
    update_data = {k: v for k, v in data.dict().items() if v is not None}

    # Manuscript protection: Never allow empty or blank-placeholder content
    # to overwrite non-empty existing prose
    if "content" in update_data:
        incoming_c = update_data["content"].strip()
        existing_c = (existing.get("content") or "").strip()
        if (incoming_c == "" or incoming_c == "<p><br></p>") and (existing_c != "" and existing_c != "<p><br></p>"):
            # Preserve existing prose
            update_data.pop("content")

    # Title protection:
    # 1. Clean whitespace
    # 2. Never allow empty/blank title to overwrite an existing valid title
    if "title" in update_data:
        incoming_t = update_data["title"].strip()
        existing_t = (existing.get("title") or "").strip()
        if not incoming_t and existing_t:
            update_data.pop("title")
        elif incoming_t:
            update_data["title"] = incoming_t
        elif not existing_t:
            update_data["title"] = f"Chapter {existing.get('chapter_number', 1)}"

    # If pages are provided, also persist them individually
    if "pages" in update_data and update_data["pages"]:
        for p in update_data["pages"]:
            p_dict = p.dict() if hasattr(p, "dict") else dict(p)
            p_dict["chapter_id"] = chapter_id
            db_service.save_page(chapter_id, p_dict, sync_chapter=False)

    existing.update(update_data)
    saved = db_service.save_chapter(existing)
    
    story_id = existing.get("story_id")
    # Immediately re-index updated chapter in ChromaDB vector store
    if story_id:
        try:
            vector_service.index_chapter(story_id, saved)
        except Exception as e:
            print(f"[Chapter Re-Indexing Error] {e}")

    return saved

@router.delete("/api/chapters/{chapter_id}")
def delete_chapter(chapter_id: str):
    # Remove from ChromaDB index first
    try:
        vector_service.delete_chapter_index(chapter_id)
    except Exception as e:
        print(f"[Chapter Deletion Index Error] {e}")
    success = db_service.delete_chapter(chapter_id)
    return {"success": success, "deleted_id": chapter_id}


# Independent Page Endpoints
@router.get("/api/chapters/{chapter_id}/pages", response_model=List[Page])
def get_chapter_pages(chapter_id: str):
    chap = db_service.get_chapter(chapter_id)
    if not chap:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return db_service.get_pages(chapter_id)

@router.post("/api/chapters/{chapter_id}/pages", response_model=Page)
def create_chapter_page(chapter_id: str, data: PageCreate):
    chap = db_service.get_chapter(chapter_id)
    if not chap:
        raise HTTPException(status_code=404, detail="Chapter not found")
    page_data = data.dict()
    return db_service.create_page(chapter_id, page_data)

@router.get("/api/chapters/{chapter_id}/pages/{page_id}", response_model=Page)
def get_chapter_page(chapter_id: str, page_id: str):
    page = db_service.get_page(chapter_id, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page

@router.put("/api/chapters/{chapter_id}/pages/{page_id}", response_model=Page)
def update_chapter_page(chapter_id: str, page_id: str, data: PageUpdate):
    page = db_service.get_page(chapter_id, page_id)
    if not page:
        # Auto-upsert page instead of 404
        page = {
            "id": page_id,
            "chapter_id": chapter_id,
            "page_number": data.page_number if data.page_number is not None else 1,
            "content": data.content or "",
            "save_status": data.save_status or "saved"
        }
        return db_service.save_page(chapter_id, page, sync_chapter=True)

    if data.content is not None:
        incoming = data.content.strip()
        existing_content = (page.get("content") or "").strip()
        if (incoming == "" or incoming == "<p><br></p>") and (existing_content != "" and existing_content != "<p><br></p>"):
            return page
        page["content"] = data.content

    if data.page_number is not None:
        page["page_number"] = data.page_number
    if data.save_status is not None:
        page["save_status"] = data.save_status

    return db_service.save_page(chapter_id, page, sync_chapter=True)

@router.delete("/api/chapters/{chapter_id}/pages/{page_id}")
def delete_chapter_page(chapter_id: str, page_id: str):
    success = db_service.delete_page(chapter_id, page_id)
    return {"success": success, "deleted_id": page_id}
