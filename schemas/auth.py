from pydantic import BaseModel
from typing import List, Optional

class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None

class DropdownItem(BaseModel):
    label: str
    path: str
    name: str
    url: str

class DropdownResponse(BaseModel):
    role: str
    token: str
    dropdownList: List[DropdownItem]