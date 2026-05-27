from fastapi import APIRouter, Depends, status

from app.schemas import (
    AvailableIP,
    AvailablePrefix,
    AvailablePrefixRequest,
    IPAddressResponse,
    PrefixCreate,
    PrefixListResponse,
    PrefixResponse,
    _family_obj,
)
from app.services.prefix_service import PrefixService, get_prefix_service

router = APIRouter(prefix="/prefixes", tags=["prefixes"])


@router.get("/", response_model=PrefixListResponse)
def list_prefixes(
    role: str | None = None,
    family: int | None = None,
    service: PrefixService = Depends(get_prefix_service),
):
    items = service.list_prefixes(role=role, family=family)
    return PrefixListResponse(
        count=len(items),
        results=[PrefixResponse.from_orm_obj(p) for p in items],
    )


@router.post("/", response_model=PrefixResponse, status_code=status.HTTP_201_CREATED)
def create_prefix(
    payload: PrefixCreate,
    service: PrefixService = Depends(get_prefix_service),
):
    obj = service.create_prefix(
        prefix=payload.prefix,
        status=payload.status,
        role=payload.role,
        description=payload.description,
    )
    return PrefixResponse.from_orm_obj(obj)


@router.get("/{prefix_id}/", response_model=PrefixResponse)
def get_prefix(prefix_id: int, service: PrefixService = Depends(get_prefix_service)):
    return PrefixResponse.from_orm_obj(service.get_prefix(prefix_id))


@router.delete("/{prefix_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_prefix(prefix_id: int, service: PrefixService = Depends(get_prefix_service)):
    service.delete_prefix(prefix_id)


@router.get("/{prefix_id}/available-ips/", response_model=list[AvailableIP])
def list_available_ips(prefix_id: int, service: PrefixService = Depends(get_prefix_service)):
    net, available = service.get_available_ips(prefix_id)
    family = _family_obj(net.version)
    return [AvailableIP(address=f"{ip}/{net.prefixlen}", family=family) for ip in available]


@router.post("/{prefix_id}/available-ips/", response_model=IPAddressResponse, status_code=status.HTTP_201_CREATED)
def allocate_ip(prefix_id: int, service: PrefixService = Depends(get_prefix_service)):
    return IPAddressResponse.from_orm_obj(service.allocate_ip(prefix_id))


@router.get("/{prefix_id}/available-prefixes/", response_model=list[AvailablePrefix])
def list_available_prefixes(prefix_id: int, service: PrefixService = Depends(get_prefix_service)):
    net, available = service.get_available_prefixes(prefix_id)
    family = _family_obj(net.version)
    return [AvailablePrefix(prefix=str(block), family=family) for block in available]


@router.post("/{prefix_id}/available-prefixes/", response_model=PrefixResponse, status_code=status.HTTP_201_CREATED)
def allocate_prefix(
    prefix_id: int,
    payload: AvailablePrefixRequest,
    service: PrefixService = Depends(get_prefix_service),
):
    return PrefixResponse.from_orm_obj(service.allocate_prefix(prefix_id, payload.prefix_length))
