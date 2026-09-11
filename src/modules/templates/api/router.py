from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["templates"])


@router.get("/templates")
async def list_templates() -> list[dict]:
    raise NotImplementedError("TODO(B2)")
