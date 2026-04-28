"""Audit logging middleware for FastAPI"""
import time
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import AsyncSessionLocal
from app.repositories.audit_log import AuditLogRepository


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all state-changing requests to audit_logs table.

    Logs POST, PUT, PATCH, DELETE requests with:
    - user_id (from JWT token if available)
    - action (HTTP method + path)
    - resource_type and resource_id (extracted from path)
    - IP address, user agent, session ID
    - Request/response details
    """

    # HTTP methods that trigger audit logging
    AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Paths to exclude from audit logging
    EXCLUDED_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",  # Login has its own audit logging
        "/api/v1/auth/refresh",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log to audit_logs if applicable.

        Args:
            request: FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response from route handler
        """
        # Execute request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Check if request should be audited
        if not self._should_audit(request):
            return response

        # Log to audit_logs (async, don't block response)
        try:
            await self._create_audit_log(request, response, process_time)
        except Exception as e:
            # Log error but don't fail the request
            print(f"Audit logging error: {str(e)}")

        return response

    def _should_audit(self, request: Request) -> bool:
        """
        Determine if request should be audited.

        Args:
            request: FastAPI request

        Returns:
            True if should be audited, False otherwise
        """
        # Only audit state-changing methods
        if request.method not in self.AUDITED_METHODS:
            return False

        # Exclude certain paths
        if request.url.path in self.EXCLUDED_PATHS:
            return False

        return True

    async def _create_audit_log(
        self, request: Request, response: Response, process_time: float
    ) -> None:
        """
        Create audit log entry.

        Args:
            request: FastAPI request
            response: FastAPI response
            process_time: Request processing time in seconds
        """
        # Extract user ID from request state (set by auth dependency)
        user_id: Optional[UUID] = getattr(request.state, "user_id", None)

        # Extract resource information from path
        resource_type, resource_id = self._extract_resource_info(request.url.path)

        # Build action string
        action = f"{request.method}_{resource_type}".upper()

        # Get client IP
        ip_address = request.client.host if request.client else None

        # Get user agent
        user_agent = request.headers.get("user-agent")

        # Get session ID (if available)
        session_id = request.headers.get("x-session-id")

        # Build details
        details = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
        }

        # Create audit log entry
        async with AsyncSessionLocal() as session:
            audit_repo = AuditLogRepository(session)
            await audit_repo.create(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=UUID(resource_id) if resource_id else None,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=UUID(session_id) if session_id else None,
                details=details,
            )
            await session.commit()

    def _extract_resource_info(self, path: str) -> tuple[str, Optional[str]]:
        """
        Extract resource type and ID from request path.

        Examples:
            /api/v1/users/123 -> ("USER", "123")
            /api/v1/alerts/456/acknowledge -> ("ALERT", "456")
            /api/v1/feeds -> ("FEED", None)

        Args:
            path: Request path

        Returns:
            Tuple of (resource_type, resource_id)
        """
        parts = path.strip("/").split("/")

        # Find resource name (usually after /api/v1/)
        resource_type = "UNKNOWN"
        resource_id = None

        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
            resource_type = parts[2].upper().rstrip("S")  # Remove trailing 's'

            # Check if next part is a UUID (resource ID)
            if len(parts) >= 4:
                potential_id = parts[3]
                # Simple UUID validation
                if len(potential_id) == 36 and potential_id.count("-") == 4:
                    resource_id = potential_id

        return resource_type, resource_id
