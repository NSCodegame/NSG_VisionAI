"""
Pytest configuration and shared fixtures for tests.
"""
import asyncio
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_session
from app.main import app as main_app
from app.models.base import Base


# Test database URL (use separate test database)
TEST_DATABASE_URL = settings.database_url.replace("/nsg_visionai", "/nsg_visionai_test")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


# Mark all async fixtures with pytest_asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override"""
    async def override_get_session():
        yield db_session
    
    main_app.dependency_overrides[get_session] = override_get_session
    
    async with AsyncClient(app=main_app, base_url="http://test") as ac:
        yield ac
    
    main_app.dependency_overrides.clear()
