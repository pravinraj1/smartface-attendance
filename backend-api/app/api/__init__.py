from fastapi import APIRouter
from app.api.v1 import api_router

api_router_v1 = APIRouter()
api_router_v1.include_router(api_router, prefix="/api/v1")
