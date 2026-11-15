from fastapi import Header, HTTPException, Depends
from typing import Optional, Dict, Any
from google.oauth2 import id_token
from google.auth.transport import requests

FIREBASE_PROJECT_ID = "mythra-d5b52"
_request_adapter = requests.Request()

def verify_token(token_str: str) -> Dict[str, Any]:
    """
    Cryptographically verifies Firebase ID tokens using Google's public key infrastructure.
    Validates token signature, project audience, issuer, and expiration timestamp.
    """
    try:
        decoded = id_token.verify_firebase_token(
            token_str,
            _request_adapter,
            audience=FIREBASE_PROJECT_ID
        )
        return decoded
    except Exception as e:
        raise HTTPException(
            status_code=401, 
            detail=f"Invalid or expired authentication credentials: {str(e)}"
        )

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Strict authentication dependency. Requires valid Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in.")
    token = authorization.split("Bearer ", 1)[1].strip()
    payload = verify_token(token)
    return {
        "uid": payload.get("sub") or payload.get("user_id"),
        "email": payload.get("email"),
        "name": payload.get("name")
    }

def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """
    Permissive authentication dependency. Returns verified user profile if token present, else None.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split("Bearer ", 1)[1].strip()
    try:
        payload = verify_token(token)
        return {
            "uid": payload.get("sub") or payload.get("user_id"),
            "email": payload.get("email"),
            "name": payload.get("name")
        }
    except Exception:
        return None
