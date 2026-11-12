
"""Isolated development application for the logistics module.

This application uses fictional data and bypasses real authentication.
Never deploy it as the production application.
"""

from datetime import date, datetime

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.modules.logistics import mock_delivery, mock_repository
from app.modules.logistics.schemas import DailyRouteResponse
from app.modules.logistics.service import get_daily_route

from fastapi.responses import Response

from datetime import timezone
from app.modules.logistics import mock_fedex

from fastapi import HTTPException, Request

from app.modules.bioinformatica import mock_service

from app.modules.bioinformatica import mock_service


app = FastAPI(
    title="GenLab Logistics Development API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class PickupResponse(BaseModel):
    laboratory_id: int
    picked_up_at: datetime
    status: str


class DeliveryStatusResponse(BaseModel):
    route_id: int
    date: date
    total_stops: int
    completed_stops: int
    can_deliver: bool
    delivered_at: datetime | None = None
    study_count: int | None = None


class DeliveryResponse(BaseModel):
    route_id: int
    date: date
    delivered_at: datetime
    study_count: int
    batch_ids: list[int]


class BatchResponse(BaseModel):
    id: int
    state: str
    study_count: int
    is_urgent: bool
    closed_at: datetime | None = None
    authorized_at: datetime | None = None
    has_csv: bool
    has_permit: bool
    authorization_error: str | None = None
    can_schedule_pickup: bool
    scheduled_pickup_at: datetime | None = None
    collected_at: datetime | None = None
    fedex_url: str | None = None

@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "mode": "development",
    }


@app.get(
    "/logistics/daily-route",
    response_model=DailyRouteResponse,
)
def view_daily_route(
    date: date = Query(default_factory=date.today),
) -> DailyRouteResponse:
    return get_daily_route(
        carrier_id=mock_repository.MOCK_CARRIER_ID,
        route_date=date,
        repository=mock_repository,
    )


@app.post(
    "/logistics/daily-route/stops/{laboratory_id}/pickup",
    response_model=PickupResponse,
)
def register_pickup(
    laboratory_id: int,
    date: date = Query(default_factory=date.today),
) -> PickupResponse:
    picked_up_at = mock_repository.register_pickup(
        carrier_id=mock_repository.MOCK_CARRIER_ID,
        route_date=date,
        laboratory_id=laboratory_id,
    )

    return PickupResponse(
        laboratory_id=laboratory_id,
        picked_up_at=picked_up_at,
        status="Completed",
    )


@app.get(
    "/logistics/delivery/status",
    response_model=DeliveryStatusResponse,
)
def view_delivery_status(
    date: date = Query(default_factory=date.today),
) -> DeliveryStatusResponse:
    return mock_delivery.get_delivery_status(
        carrier_id=mock_repository.MOCK_CARRIER_ID,
        route_date=date,
    )


@app.post(
    "/logistics/delivery",
    response_model=DeliveryResponse,
)
def register_delivery(
    date: date = Query(default_factory=date.today),
) -> DeliveryResponse:
    return mock_delivery.register_delivery(
        carrier_id=mock_repository.MOCK_CARRIER_ID,
        route_date=date,
    )


@app.get(
    "/logistics/batches",
    response_model=list[BatchResponse],
)
def view_batches() -> list[BatchResponse]:
    return mock_delivery.get_batches()


@app.get("/logistics/batches/{batch_id}/csv")
def download_batch_csv(batch_id: int) -> Response:
    content = mock_delivery.get_batch_document(
        batch_id,
        "csv",
    )

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="lote-{batch_id}-pacientes.csv"'
            )
        },
    )


@app.get("/logistics/batches/{batch_id}/permit")
def download_batch_permit(batch_id: int) -> Response:
    content = mock_delivery.get_batch_document(
        batch_id,
        "permit",
    )

    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="lote-{batch_id}-permiso-simulado.pdf"'
            )
        },
    )


class SchedulePickupRequest(BaseModel):
    scheduled_at: datetime


class ShipmentResponse(BaseModel):
    batch_id: int
    scheduled_pickup_at: datetime
    collected_at: datetime | None = None
    status: str
    tracking_url: str


@app.post(
    "/logistics/batches/{batch_id}/schedule-pickup",
    response_model=ShipmentResponse,
)
def schedule_pickup(
    batch_id: int,
    request: SchedulePickupRequest,
) -> dict:
    if request.scheduled_at.utcoffset() is None:
        from fastapi import HTTPException

        raise HTTPException(
            400,
            "La fecha y hora deben incluir una zona horaria.",
        )

    return mock_delivery.schedule_batch_pickup(
        batch_id=batch_id,
        scheduled_at=request.scheduled_at,
    )


@app.get(
    "/logistics/fedex/tracking/{batch_id}",
    response_model=ShipmentResponse,
)
def get_fedex_tracking(batch_id: int) -> dict:
    return mock_fedex.get_shipment(batch_id)


@app.post(
    "/logistics/fedex/tracking/{batch_id}/simulate-collection",
    response_model=ShipmentResponse,
)
def simulate_fedex_collection(batch_id: int) -> dict:
    return mock_delivery.register_fedex_collection(batch_id)


@app.get("/logistics/fedex/holidays", response_model=list[str])
def get_fedex_holidays() -> list[str]:
    return mock_fedex.get_configured_holidays()


class MockStudyResponse(BaseModel):
    id: int
    batch_id: int
    state: str
    pompe_urgent: bool


@app.get(
    "/logistics/batches/{batch_id}/studies",
    response_model=list[MockStudyResponse],
)
def view_batch_studies(batch_id: int) -> list[dict]:
    return mock_delivery.get_batch_studies(batch_id)


class RawDataStudyResponse(BaseModel):
    id: int
    batch_id: int
    state: str
    pompe_urgent: bool


class RawDataUploadResponse(BaseModel):
    study_id: int
    state: str
    filename: str
    file_size: int
    uploaded_at: datetime
    notification_status: str


class BioinformaticsNotificationResponse(BaseModel):
    study_id: int
    recipient_role: str
    channel: str
    status: str
    created_at: datetime


@app.get(
    "/bioinformatics/raw-data/pending",
    response_model=list[RawDataStudyResponse],
)
def list_studies_awaiting_raw_data() -> list[dict]:
    return mock_delivery.get_studies_awaiting_raw_data()


@app.post(
    "/bioinformatics/studies/{study_id}/raw-data",
    response_model=RawDataUploadResponse,
)
async def upload_raw_data(
    study_id: int,
    request: Request,
) -> dict:
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/octet-stream":
        raise HTTPException(
            status_code=415,
            detail="El archivo debe enviarse como datos binarios.",
        )

    filename = request.headers.get("X-File-Name", "").strip()

    content = await request.body()

    return mock_delivery.upload_study_raw_data(
        study_id=study_id,
        filename=filename,
        content=content,
    )


@app.get(
    "/bioinformatics/notifications",
    response_model=list[BioinformaticsNotificationResponse],
)
def list_bioinformatics_notifications() -> list[dict]:
    return mock_delivery.get_bioinformatics_notifications()



class AvailableStudyResponse(BaseModel):
    id: int
    batch_id: int
    state: str
    pompe_urgent: bool
    arrived_at: datetime
    pathology: str


class StudyGenesResponse(BaseModel):
    study_id: int
    pathology: str
    genes: list[str]
    simulated: bool


class TakeStudyRequest(BaseModel):
    analyst_id: str


class StudyAssignmentResponse(BaseModel):
    study_id: int
    batch_id: int
    analyst_id: str
    analyst_name: str
    assigned_at: datetime
    state: str


@app.get(
    "/bioinformatics/studies/available",
    response_model=list[AvailableStudyResponse],
)
def list_available_bioinformatics_studies() -> list[dict]:
    return mock_service.list_available_studies()


@app.get(
    "/bioinformatics/studies/{study_id}/genes",
    response_model=StudyGenesResponse,
)
def view_study_genes(study_id: int) -> dict:
    return mock_service.get_study_genes(study_id)


@app.post(
    "/bioinformatics/studies/{study_id}/take",
    response_model=StudyAssignmentResponse,
)
def take_bioinformatics_study(
    study_id: int,
    request: TakeStudyRequest,
) -> dict:
    return mock_service.take_study(
        study_id=study_id,
        analyst_id=request.analyst_id,
    )


@app.get(
    "/bioinformatics/studies/assigned",
    response_model=list[StudyAssignmentResponse],
)
def list_my_bioinformatics_studies(
    analyst_id: str = Query(...),
) -> list[dict]:
    return mock_service.list_assigned_studies(analyst_id)




class AnalysisGenesResponse(BaseModel):
    study_id: int
    genes: list[str]
    simulated: bool


class AnalysisVariantResponse(BaseModel):
    gene: str
    variant: str
    classification: str


class GeneVariantsResponse(BaseModel):
    study_id: int
    gene: str
    variants: list[AnalysisVariantResponse]
    simulated: bool


class AnalysisResponse(BaseModel):
    study_id: int
    variants: list[AnalysisVariantResponse]


class RegisterVariantRequest(BaseModel):
    analyst_id: str
    gene: str
    variant: str


class RemoveVariantRequest(BaseModel):
    analyst_id: str
    gene: str
    variant: str


class CompleteAnalysisRequest(BaseModel):
    analyst_id: str


class CompleteAnalysisResponse(BaseModel):
    study_id: int
    state: str
    variant_count: int
    negative: bool
    completed_at: datetime
    pdf_available: bool
    notification_count: int


@app.get(
    "/bioinformatics/studies/{study_id}/analysis/genes",
    response_model=AnalysisGenesResponse,
)
def view_analysis_genes(
    study_id: int,
    analyst_id: str = Query(...),
) -> dict:
    return mock_service.get_analysis_genes(study_id, analyst_id)


@app.get(
    "/bioinformatics/studies/{study_id}/analysis/genes/{gene}/variants",
    response_model=GeneVariantsResponse,
)
def view_gene_variants(
    study_id: int,
    gene: str,
    analyst_id: str = Query(...),
) -> dict:
    return mock_service.get_gene_variants(study_id, analyst_id, gene)


@app.get(
    "/bioinformatics/studies/{study_id}/analysis",
    response_model=AnalysisResponse,
)
def view_analysis(
    study_id: int,
    analyst_id: str = Query(...),
) -> dict:
    return mock_service.get_analysis(study_id, analyst_id)


@app.post(
    "/bioinformatics/studies/{study_id}/analysis/variants",
    response_model=AnalysisVariantResponse,
)
def add_analysis_variant(
    study_id: int,
    request: RegisterVariantRequest,
) -> dict:
    return mock_service.register_variant(
        study_id,
        request.analyst_id,
        request.gene,
        request.variant,
    )


@app.post(
    "/bioinformatics/studies/{study_id}/analysis/variants/remove",
)
def delete_analysis_variant(
    study_id: int,
    request: RemoveVariantRequest,
) -> dict:
    return mock_service.remove_variant(
        study_id,
        request.analyst_id,
        request.gene,
        request.variant,
    )


@app.post(
    "/bioinformatics/studies/{study_id}/analysis/complete",
    response_model=CompleteAnalysisResponse,
)
def finish_analysis(
    study_id: int,
    request: CompleteAnalysisRequest,
) -> dict:
    return mock_service.complete_analysis(
        study_id,
        request.analyst_id,
    )


@app.get("/bioinformatics/studies/{study_id}/analysis/result.pdf")
def download_analysis_result(
    study_id: int,
    analyst_id: str = Query(...),
) -> Response:
    content = mock_service.get_result_pdf(study_id, analyst_id)

    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="resultado-estudio-{study_id}.pdf"'
            )
        },
    )



class ResultSummaryResponse(BaseModel):
    study_id: int
    state: str
    variant_count: int
    negative: bool
    completed_at: datetime


class ResultDetailResponse(ResultSummaryResponse):
    pdf_available: bool
    variants: list[AnalysisVariantResponse] | None = None


@app.get(
    "/bioinformatics/results",
    response_model=list[ResultSummaryResponse],
)
def list_bioinformatics_results(
    role: str = Query(...),
    actor_id: str = Query(...),
) -> list[dict]:
    return mock_service.list_results(role, actor_id)


@app.get(
    "/bioinformatics/results/{study_id}",
    response_model=ResultDetailResponse,
)
def view_bioinformatics_result(
    study_id: int,
    role: str = Query(...),
    actor_id: str = Query(...),
) -> dict:
    return mock_service.get_result(study_id, role, actor_id)


@app.get("/bioinformatics/results/{study_id}/pdf")
def download_bioinformatics_result(
    study_id: int,
    role: str = Query(...),
    actor_id: str = Query(...),
) -> Response:
    content = mock_service.get_result_pdf_for_actor(
        study_id,
        role,
        actor_id,
    )

    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="resultado-estudio-{study_id}.pdf"'
            )
        },
    )



from app.modules.bioinformatica import mock_reanalysis


class ReanalysisPathologyResponse(BaseModel):
    name: str
    simulated: bool


class ReanalysisPreviewResponse(BaseModel):
    study_id: int
    pathology: str
    candidate_genes: list[str]
    analyzed_genes: list[str]
    pending_genes: list[str]
    excluded_genes: list[str]
    can_request: bool
    has_pending_request: bool
    simulated: bool


class ReanalysisRequestBody(BaseModel):
    doctor_id: str
    pathology: str


class ReanalysisRequestResponse(BaseModel):
    id: int
    study_id: int
    doctor_id: str
    pathology: str
    candidate_genes: list[str]
    excluded_genes: list[str]
    pending_genes: list[str]
    requested_at: datetime
    status: str
    original_completed_at: datetime
    uses_existing_raw_data: bool
    payment_required: bool | None
    simulated: bool


@app.get(
    "/bioinformatics/reanalysis/pathologies",
    response_model=list[ReanalysisPathologyResponse],
)
def list_reanalysis_pathologies() -> list[dict]:
    return mock_reanalysis.list_pathologies()


@app.get(
    "/bioinformatics/studies/{study_id}/reanalysis/preview",
    response_model=ReanalysisPreviewResponse,
)
def preview_study_reanalysis(
    study_id: int,
    doctor_id: str = Query(...),
    pathology: str = Query(...),
) -> dict:
    return mock_reanalysis.preview_reanalysis(
        study_id,
        doctor_id,
        pathology,
    )


@app.post(
    "/bioinformatics/studies/{study_id}/reanalysis",
    response_model=ReanalysisRequestResponse,
    status_code=201,
)
def create_study_reanalysis(
    study_id: int,
    request: ReanalysisRequestBody,
) -> dict:
    return mock_reanalysis.request_reanalysis(
        study_id,
        request.doctor_id,
        request.pathology,
    )


@app.get(
    "/bioinformatics/studies/{study_id}/reanalysis",
    response_model=ReanalysisRequestResponse | None,
)
def view_study_reanalysis(
    study_id: int,
    doctor_id: str = Query(...),
) -> dict | None:
    return mock_reanalysis.get_reanalysis_request(
        study_id,
        doctor_id,
    )



from app.modules.notifications import mock_service as notification_service


class NoticeResponse(BaseModel):
    id: str
    study_id: int
    title: str
    message: str
    created_at: datetime
    destination: str | None
    pending: bool
    simulated: bool


class NoticeSummaryResponse(BaseModel):
    total: int
    pending_count: int
    has_pending: bool
    simulated: bool


@app.get(
    "/notifications",
    response_model=list[NoticeResponse],
)
def list_user_notifications(
    role: str = Query(...),
    actor_id: str = Query(...),
) -> list[dict]:
    return notification_service.list_notices(role, actor_id)


@app.get(
    "/notifications/summary",
    response_model=NoticeSummaryResponse,
)
def get_user_notifications_summary(
    role: str = Query(...),
    actor_id: str = Query(...),
) -> dict:
    return notification_service.get_notice_summary(role, actor_id)
