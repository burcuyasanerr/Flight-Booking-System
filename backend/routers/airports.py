from fastapi import APIRouter

from backend.schemas import Airport
from backend.services import db_manager

router = APIRouter(tags=["Havalimanları"])


@router.get("/airports", response_model=list[Airport], summary="Tüm havalimanları ve koordinatları")
def list_airports():
    query = """
    SELECT id, iata_code, name, city, latitude, longitude
    FROM airports
    ORDER BY id;
    """
    with db_manager.get_cursor(commit=False) as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    return [
        Airport(id=r[0], iata_code=r[1], name=r[2], city=r[3], latitude=r[4], longitude=r[5])
        for r in rows
    ]
