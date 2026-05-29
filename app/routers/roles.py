from fastapi import APIRouter, Depends, status

from app.schemas import RoleCreate, RoleResponse
from app.services.role_service import RoleService, get_role_service

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/", response_model=list[RoleResponse])
def list_roles(service: RoleService = Depends(get_role_service)):
    return [RoleResponse(id=r.id, name=r.name, description=r.description) for r in service.list_roles()]


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, service: RoleService = Depends(get_role_service)):
    r = service.create_role(name=payload.name, description=payload.description)
    return RoleResponse(id=r.id, name=r.name, description=r.description)
