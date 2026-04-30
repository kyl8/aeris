from datetime import date

from fastapi import APIRouter, Query

from ..core.storage import get_history_store
from ..schemas.prediction import PredictionHistoryItem, PredictionHistoryResponse

router = APIRouter(tags=["history"])


@router.get(
    "/api/v1/history",
    response_model=PredictionHistoryResponse,
    summary="Lista as predições recentes",
)
def history(
    date_filter: date | None = Query(default=None, alias="date", description="Filtra por data UTC (YYYY-MM-DD)."),
    prediction_class: str | None = Query(default=None, alias="class", description="Filtra pela classe prevista."),
) -> PredictionHistoryResponse:
    store = get_history_store()
    records = store.list(date_filter=date_filter, prediction_class=prediction_class)

    items = [PredictionHistoryItem.model_validate(record.to_payload()) for record in records]
    return PredictionHistoryResponse(items=items, total=len(items))