# app/api/middlewares/__init__.py
"""Middleware package for the API."""

from app.api.middlewares.csrf import CSRFMiddleware

__all__ = ["CSRFMiddleware"]
