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
def create_chapter(story_id: str, data: ChapterCreate):
    data_dict = data.dict()
    data_dict["story_id"] = story_id
    data_dict["id"] = f"chap_{uuid.uuid4().hex[:10]}"
    saved = db_service.save_chapter(data_dict)
    # Immediately index new chapter into ChromaDB semantic store
    try:
        vector_service.index_chapter(story_id, saved)
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
    existing.update(update_data)
    saved = db_service.save_chapter(existing)
    
    story_id = existing.get("story_id")
    # Immediately re-index updated chapter in ChromaDB vector store
    if story_id:
        try:
            vector_service.index_chapter(story_id, saved)
        except Exception as e:
            print(f"[Chapter Re-Indexing Error] {e}")

    # Auto-extract new characters mentioned in the manuscript update
    if "content" in update_data and len(update_data["content"]) > 60:
        if story_id:
            try:
                story = db_service.get_story(story_id)
                genre = story.get("genre", "Fiction") if story else "Fiction"
                existing_chars = db_service.get_characters(story_id)
                existing_names = {c.get("name", "").strip().lower() for c in existing_chars}
                extracted = ai_service.extract_characters_from_text(
                    text=update_data["content"],
                    existing_characters=existing_chars,
                    story_genre=genre
                )
                for item in extracted:
                    c_name = item.get("name", "").strip()
                    if c_name and c_name.lower() not in existing_names:
                        new_char = {
                            "id": f"char_{uuid.uuid4().hex[:10]}",
                            "story_id": story_id,
                            "name": c_name,
                            "alias": item.get("alias", ""),
                            "age": str(item.get("age", "")),
                            "role": item.get("role", "Supporting"),
                            "personality_traits": item.get("personality_traits", ["Determined"]),
                            "physical_description": item.get("physical_description", ""),
                            "backstory": item.get("backstory", f"Introduced in Chapter {existing.get('chapter_number', 1)}."),
                            "motivations": item.get("motivations", ""),
                            "goals": item.get("goals", ""),
                            "fears": item.get("fears", ""),
                            "secrets": item.get("secrets", ""),
                            "current_status": item.get("status", "Alive"),
                            "first_appearance": f"Chapter {existing.get('chapter_number', 1)}",
                            "last_appearance": f"Chapter {existing.get('chapter_number', 1)}",
                            "relationships": []
                        }
                        db_service.save_character(new_char)
                        existing_names.add(c_name.lower())
            except Exception as e:
                print(f"[Chapter Save Auto-Sync Notice] {e}")

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
        raise HTTPException(status_code=404, detail="Page not found")

    if data.content is not None:
        incoming = data.content.strip()
        existing_content = page.get("content", "").strip()
        if (incoming == "" or incoming == "<p><br></p>") and (existing_content != "" and existing_content != "<p><br></p>"):
            if data.save_status in ["init", "default"]:
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
