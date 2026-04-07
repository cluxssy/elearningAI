from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

# --- Chat/Editing Schemas ---
class ChatMessageBase(BaseModel):
    type: str
    role: str
    content: str
    
class ChatMessageCreate(ChatMessageBase):
    project_id: str

class ChatMessageResponse(ChatMessageBase):
    id: int
    project_id: str
    timestamp: datetime
    
    class Config:
        from_attributes = True
        
class DocumentEditRequest(BaseModel):
    doc_type: str
    user_prompt: str
    current_content: str
    selected_text: Optional[str] = None
    selected_screen_num: Optional[str] = None
    selected_col_index: Optional[int] = None
    selected_col_name: Optional[str] = None

# --- Project Schemas ---
class ProjectBase(BaseModel):
    title: str
    business_unit: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: str
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ProjectDetailResponse(ProjectResponse):
    intake_data: Optional[str] = None
    extracted_content: Optional[str] = None
    design_doc: Optional[str] = None
    storyboard: Optional[str] = None
    messages: List[ChatMessageResponse] = []

# --- Folder & File Schemas ---
class UserFileBase(BaseModel):
    name: str
    folder_id: Optional[int] = None
    file_size: Optional[int] = None

class UserFileResponse(UserFileBase):
    id: int
    user_id: int
    file_type: str
    file_path: str
    created_at: datetime

    class Config:
        from_attributes = True

class FolderBase(BaseModel):
    name: str
    parent_id: Optional[int] = None

class FolderCreate(FolderBase):
    pass

class FolderResponse(FolderBase):
    id: int
    user_id: int
    created_at: datetime
    files: List[UserFileResponse] = []
    
    class Config:
        from_attributes = True

class FolderDetailResponse(FolderResponse):
    subfolders: List[FolderResponse] = []

# --- Auth Request Schemas ---
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
