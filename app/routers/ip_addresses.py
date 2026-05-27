from fastapi import APIRouter, Depends, status

from app.schemas import (
    IPAddressCreate,
    IPAddressListResponse,
    IPAddressPatch,
    IPAddressResponse,
)
from app.services.ip_address_service import IPAddressService, get_ip_address_service

router = APIRouter(prefix="/ip-addresses", tags=["ip-addresses"])


@router.get("/", response_model=IPAddressListResponse)
def list_ip_addresses(
    address: str | None = None,
    mask_length: int | None = None,
    service: IPAddressService = Depends(get_ip_address_service),
):
    items = service.list_ip_addresses(address=address, mask_length=mask_length)
    return IPAddressListResponse(
        count=len(items),
        results=[IPAddressResponse.from_orm_obj(r) for r in items],
    )


@router.post("/", response_model=IPAddressResponse, status_code=status.HTTP_201_CREATED)
def create_ip_address(
    payload: IPAddressCreate,
    service: IPAddressService = Depends(get_ip_address_service),
):
    obj = service.create_ip_address(
        address=payload.address,
        status=payload.status,
        role=payload.role,
        dns_name=payload.dns_name,
        description=payload.description,
    )
    return IPAddressResponse.from_orm_obj(obj)


@router.get("/{ip_id}/", response_model=IPAddressResponse)
def get_ip_address(ip_id: int, service: IPAddressService = Depends(get_ip_address_service)):
    return IPAddressResponse.from_orm_obj(service.get_ip_address(ip_id))


@router.patch("/{ip_id}/", response_model=IPAddressResponse)
def patch_ip_address(
    ip_id: int,
    payload: IPAddressPatch,
    service: IPAddressService = Depends(get_ip_address_service),
):
    return IPAddressResponse.from_orm_obj(
        service.patch_ip_address(ip_id, payload.model_dump(exclude_unset=True))
    )


@router.delete("/{ip_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_ip_address(ip_id: int, service: IPAddressService = Depends(get_ip_address_service)):
    service.delete_ip_address(ip_id)
