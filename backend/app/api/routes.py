"""REST API endpoints."""

import logging

from fastapi import APIRouter, HTTPException, status

from backend.app.commands.router import command_router
from backend.app.core.config import get_settings
from backend.app.core.schemas import (
    ChatRequest,
    ChatResponse,
    CommandInfo,
    HealthResponse,
    ModelInfo,
    ModelSelectionRequest,
    ModelSelectionResponse,
)
from backend.app.providers.base import ProviderError
from backend.app.providers.registry import registry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report that the API process is responsive."""
    return HealthResponse(app=get_settings().app_name)


@router.get("/models", response_model=list[ModelInfo])
async def models() -> list[ModelInfo]:
    """List providers configured for selection in the UI."""
    return registry.models()


@router.post("/models/select", response_model=ModelSelectionResponse)
async def select_model(request: ModelSelectionRequest) -> ModelSelectionResponse:
    """Select a configured provider at runtime."""
    choices = registry.definitions()
    definition = choices.get(request.provider_id)
    if definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown provider.")
    if not definition.available:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=definition.detail or "Provider is not configured.")
    registry.active_provider_id = request.provider_id
    return ModelSelectionResponse(active_provider=request.provider_id, model=definition.model)


@router.get("/commands", response_model=list[CommandInfo])
async def commands() -> list[CommandInfo]:
    """Return the available command skills."""
    return command_router.list_commands()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Route known system commands, otherwise ask the selected language model."""
    last_user_message = next((message.content for message in reversed(request.messages) if message.role == "user"), None)
    if last_user_message is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one user message is required.")
    try:
        command_response = await command_router.route(last_user_message)
        if command_response is not None:
            return ChatResponse(response=command_response, command_handled=True)
        provider = registry.create()
        return ChatResponse(response=await provider.generate(request.messages))
    except ValueError as exc:
        logger.warning("Chat request configuration error: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ProviderError as exc:
        logger.exception("Language model request failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
