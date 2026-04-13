# Backend Architecture (Production Layout)

This backend now uses a layered package layout with CQRS-ready boundaries.

## Package Structure

- `app/main.py`: FastAPI bootstrap and middleware.
- `app/core/`: global configuration and runtime settings.
- `app/domain/`: domain models and enums.
- `app/services/`: business/application services.
- `app/infrastructure/`: adapters for persistence, queue, websockets, provider clients.
- `app/cqrs/commands/`: write-side command DTOs.
- `app/cqrs/queries/`: read-side query DTOs.
- `app/cqrs/handlers/`: command/query handlers used by API routes.
- `routes/`: HTTP endpoint modules (kept stable; progressively moving to `app/api/routes`).

## Entry Points

- Production run: `./start.sh`
- Uvicorn target: `app.main:app`

## Import Policy

All backend imports should use package-native paths from `app.*`.

Example:

- `from app.core.config import BACKEND_PORT`
- `from app.infrastructure.store import store`

## CQRS Usage (Current)

Queue operations in execution routes now go through CQRS handlers:

- `EnqueueRunCommand`
- `CancelQueueItemCommand`
- `QueueSnapshotQuery`
- `QueueHealthQuery`
- `QueueItemQuery`

These live under `app/cqrs/*` and decouple route code from queue implementation details.
