from fastapi import APIRouter, HTTPException
from typing import Union

router = APIRouter(
    prefix="/ryan",
    tags=["ryan-gosling"],
    responses={404: {"description": "YOU ARE NOT RYAN GOSLING"}},
)
@router.get("/")
def read_base_ryan(q: str = None):
    if q == "baseline":
        raise HTTPException(status_code=404, detail="un-baselined")
    return "lurk harder ryan."

@router.get("/{gosling_id}")
def read_ryan_gosling(gosling_id: int, q: Union[str, None] = None):
    return {"You're Gosling #": gosling_id, "Why don't you say the baseline": q}