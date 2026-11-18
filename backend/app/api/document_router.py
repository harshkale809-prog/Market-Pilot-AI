from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from app.api.dependencies import get_current_token_payload
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["Knowledge Base"])
doc_service = DocumentService()

MAX_FILE_SIZE = 15 * 1024 * 1024 # 15 MB limit

@router.post("/upload/pdf")
async def upload_pdf(
    file: UploadFile = File(...), 
    token_payload: dict = Depends(get_current_token_payload)
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only PDF files (.pdf) are supported."
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds maximum 15MB limit.")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File does not have a valid PDF header.")

    org_id = token_payload.get("org_id")
    try:
        await doc_service.process_pdf_content(content, file.filename, org_id)
        return {"message": f"Successfully ingested {file.filename} for your organization."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process PDF: {str(e)}")

@router.post("/upload/url")
async def upload_url(
    url: str = Form(...), 
    token_payload: dict = Depends(get_current_token_payload)
):
    clean_url = url.strip()
    if not clean_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL cannot be empty.")
    
    org_id = token_payload.get("org_id")
    try:
        doc_service.process_url(clean_url, org_id)
        return {"message": f"Successfully scraped and ingested {clean_url}."}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to scrape URL: {str(e)}")