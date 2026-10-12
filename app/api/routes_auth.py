
import os
import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, NOTION_API_KEY
from connectors.base import GoogleServiceManager

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/status")
def get_connectors_status():

    gmail_has_creds = GMAIL_CREDENTIALS_FILE.exists()
    gmail_has_token = GMAIL_TOKEN_FILE.exists()

    if gmail_has_token:
        gmail_status = "connected"
    elif gmail_has_creds:
        gmail_status = "needs_login"
    else:
        gmail_status = "unconfigured"

    notion_configured = bool(NOTION_API_KEY and NOTION_API_KEY.strip())

    return {
        "gmail": {
            "status": gmail_status,
            "has_credentials": gmail_has_creds,
            "is_authenticated": gmail_has_token,
        },
        "notion": {
            "status": "connected" if notion_configured else "unconfigured",
            "is_authenticated": notion_configured,
        }
    }


@router.post("/gmail/upload-credentials")
async def upload_gmail_credentials(file: UploadFile = File(...)):

    content = await file.read()
    try:
        parsed = json.loads(content)
        if "installed" not in parsed and "web" not in parsed:
            raise ValueError("File is not a valid Google OAuth Client Secrets JSON.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")

    GMAIL_CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GMAIL_CREDENTIALS_FILE, "wb") as f:
        f.write(content)

    return {"status": "saved", "path": str(GMAIL_CREDENTIALS_FILE)}


@router.post("/gmail/login")
def login_gmail():

    if not GMAIL_CREDENTIALS_FILE.exists():
        raise HTTPException(status_code=400, detail="credentials.json not uploaded yet.")

    try:
        manager = GoogleServiceManager()
        creds = manager.authenticate(["https://www.googleapis.com/auth/gmail.readonly"])
        return {"status": "success", "authenticated": creds.valid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth Flow Failed: {str(e)}")


@router.post("/gmail/disconnect")
def disconnect_gmail():

    if GMAIL_TOKEN_FILE.exists():
        GMAIL_TOKEN_FILE.unlink()
    return {"status": "disconnected"}