from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from data_analyst.api.schemas import AskRequest, AskResponse, HealthResponse
from data_analyst.config import Settings
from data_analyst.service import DataAnalystService

logger = logging.getLogger(__name__)


def create_app(service: DataAnalystService | None = None) -> FastAPI:
    app = FastAPI(
        title="Agentic Data Analyst",
        version="0.1.0",
    )
    app.state.analysis_service = service

    def get_service() -> DataAnalystService:
        if app.state.analysis_service is None:
            try:
                settings = Settings()
                app.state.analysis_service = DataAnalystService.from_settings(settings)
            except ValidationError as exc:
                raise HTTPException(
                    status_code=503,
                    detail="Configuração do modelo indisponível.",
                ) from exc
        return app.state.analysis_service

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/ask", response_model=AskResponse)
    def ask(payload: AskRequest) -> AskResponse:
        try:
            state = get_service().ask(payload.question)
            return AskResponse.from_state(state)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Falha ao processar pergunta")
            raise HTTPException(
                status_code=500,
                detail="Falha ao processar a pergunta.",
            ) from exc

    return app


app = create_app()
