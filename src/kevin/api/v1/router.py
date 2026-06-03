from fastapi import APIRouter

from kevin.api.v1.routers.assets import router as assets_router
from kevin.api.v1.routers.auth import router as auth_router
from kevin.api.v1.routers.chat import router as chat_router
from kevin.api.v1.routers.expenses import router as expenses_router
from kevin.api.v1.routers.export import router as export_router
from kevin.api.v1.routers.households import router as households_router
from kevin.api.v1.routers.income import router as income_router
from kevin.api.v1.routers.liabilities import router as liabilities_router
from kevin.api.v1.routers.overview import router as overview_router
from kevin.api.v1.routers.tickers import router as tickers_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(households_router)
router.include_router(overview_router)
router.include_router(expenses_router)
router.include_router(income_router)
router.include_router(liabilities_router)
router.include_router(assets_router)
router.include_router(tickers_router)
router.include_router(export_router)
router.include_router(chat_router)
