from pydantic import BaseModel
from typing import Optional


class RoleBase(BaseModel):
    role_name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleResponse(RoleBase):
    id: str
    
    class Config:
        from_attributes = True
