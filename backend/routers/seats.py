from fastapi import APIRouter, Body, Path, Query

from backend.errors import api_error
from backend.schemas import ErrorResponse, LockRequest, LockResponse, ReleaseResponse
from backend.services import lock_manager

router = APIRouter(tags=["Koltuk kilitleme"])

# SeatLockManager'ın döndürdüğü çakışma nedenlerinin HTTP karşılıkları
CONFLICT_STATUS = {
    "SEAT_NOT_FOUND": 404,
}


@router.post(
    "/seats/{seat_id}/lock",
    response_model=LockResponse,
    summary="Koltuğu geçici olarak tut",
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def lock_seat(seat_id: int = Path(gt=0), body: LockRequest = Body(...)):
    """
    Koltuğu `LOCK_DURATION_MINUTES` (varsayılan 10) dakika boyunca bu oturuma ayırır.
    Aynı oturum tekrar isterse süre uzatılır.

    Olası çakışma kodları (409): `ALREADY_BOOKED`, `LOCKED_BY_ANOTHER_USER`,
    `VERSION_MISMATCH_RACE_CONDITION`, `FLIGHT_CANCELLED_OR_PAST`, `MAX_LOCK_LIMIT_REACHED`.
    """
    if body.expected_version is not None:
        result = lock_manager.lock_seat_optimistic(seat_id, body.session_id, body.expected_version)
    else:
        result = lock_manager.lock_seat_pessimistic(seat_id, body.session_id)

    if not result.success:
        code = result.conflict_reason or "LOCK_FAILED"
        raise api_error(CONFLICT_STATUS.get(code, 409), code, result.message)

    return LockResponse(
        seat_id=seat_id,
        session_id=body.session_id,
        locked_until=result.locked_until,
        version=result.new_version,
        message=result.message,
    )


@router.delete(
    "/seats/{seat_id}/lock",
    response_model=ReleaseResponse,
    summary="Koltuğu bırak",
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def release_seat(
    seat_id: int = Path(gt=0),
    session_id: str = Query(min_length=1, max_length=100, description="Kilidi alan oturum"),
):
    """Yalnızca kilidi alan oturum koltuğu bırakabilir."""
    result = lock_manager.release_seat_lock(seat_id, session_id)
    if not result.success:
        # Neden başarısız olduğunu ayırt etmek için koltuk yalnızca bu durumda sorgulanır
        if lock_manager.get_seat(seat_id) is None:
            raise api_error(404, "SEAT_NOT_FOUND", "Koltuk bulunamadı.")
        raise api_error(409, "LOCK_NOT_OWNED", result.message)

    return ReleaseResponse(seat_id=seat_id, message=result.message)
