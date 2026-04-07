from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas, models
from ..dependencies import get_db, get_current_user
from ..services import history_service, ai_editing
import os

router = APIRouter()

@router.post("/chat")
def ai_chat_edit(request: schemas.DocumentEditRequest, project_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    project = history_service.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    api_key = os.getenv("GROQ_API_KEY")
    
    # Get chat history for this specific doc type
    chat_history_db = db.query(models.ChatMessage).filter(
        models.ChatMessage.project_id == project_id, 
        models.ChatMessage.type == request.doc_type
    ).order_by(models.ChatMessage.timestamp.asc()).all()
    
    chat_history = [{"role": msg.role, "content": msg.content} for msg in chat_history_db]
    
    # Save user message
    user_msg = models.ChatMessage(project_id=project_id, type=request.doc_type, role="user", content=request.user_prompt)
    db.add(user_msg)
    db.commit()
    
    # Call AI
    response = ai_editing.ai_edit_document(
        api_key, 
        request.current_content, 
        request.user_prompt, 
        request.doc_type, 
        chat_history,
        selected_text=request.selected_text,
        selected_screen_num=request.selected_screen_num,
        selected_col_index=request.selected_col_index,
        selected_col_name=request.selected_col_name
    )
    
    # Save assistant message
    ai_msg = models.ChatMessage(project_id=project_id, type=request.doc_type, role="assistant", content=response["assistant_reply"])
    db.add(ai_msg)
    
    # WE NO LONGER update document in DB automatically. 
    # The frontend will now present a "Diff" and allow the user to Accept/Reject.
    # If accepted, the frontend calls /save-inline.
            
    db.commit()
    
    return response

@router.post("/save-inline")
def save_inline_edit(doc_type: str, content: dict, project_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Saves direct inline edits from the user."""
    project = history_service.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if "design" in doc_type.lower():
        project.design_doc = content.get('content')
    else:
        project.storyboard = content.get('content')
        
    db.commit()
    return {"message": "Saved successfully"}
