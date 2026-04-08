"""
Announcement endpoints for the High School Management System API
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_announcements(active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Get announcements. By default returns only currently active announcements.
    Set active_only=false to retrieve all announcements (for management).
    """
    today = datetime.now().strftime("%Y-%m-%d")

    if active_only:
        query = {
            "expiration_date": {"$gte": today},
            "$or": [
                {"start_date": {"$exists": False}},
                {"start_date": ""},
                {"start_date": {"$lte": today}}
            ]
        }
    else:
        query = {}

    announcements = []
    for doc in announcements_collection.find(query).sort("expiration_date", 1):
        doc["_id"] = str(doc["_id"])
        announcements.append(doc)

    return announcements


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    expiration_date: str,
    start_date: Optional[str] = "",
    teacher_username: str = Query(...)
) -> Dict[str, Any]:
    """Create a new announcement - requires teacher authentication"""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate expiration_date format
    try:
        datetime.strptime(expiration_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid expiration_date format. Use YYYY-MM-DD.")

    # Validate start_date format if provided
    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD.")

    announcement = {
        "message": message,
        "start_date": start_date or "",
        "expiration_date": expiration_date,
        "created_by": teacher_username
    }

    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = str(result.inserted_id)

    logger.info("Announcement created by %s: %s", teacher_username, message[:50])
    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = "",
    teacher_username: str = Query(...)
) -> Dict[str, Any]:
    """Update an existing announcement - requires teacher authentication"""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    existing = announcements_collection.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Validate expiration_date format
    try:
        datetime.strptime(expiration_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid expiration_date format. Use YYYY-MM-DD.")

    # Validate start_date format if provided
    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD.")

    update_data = {
        "message": message,
        "start_date": start_date or "",
        "expiration_date": expiration_date
    }

    announcements_collection.update_one({"_id": obj_id}, {"$set": update_data})

    updated = announcements_collection.find_one({"_id": obj_id})
    updated["_id"] = str(updated["_id"])

    logger.info("Announcement %s updated by %s", announcement_id, teacher_username)
    return updated


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: str = Query(...)
) -> Dict[str, str]:
    """Delete an announcement - requires teacher authentication"""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    result = announcements_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    logger.info("Announcement %s deleted by %s", announcement_id, teacher_username)
    return {"message": "Announcement deleted"}
