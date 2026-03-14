from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

# Common dependencies
DbDep = Annotated[AsyncSession, Depends(get_db)]
