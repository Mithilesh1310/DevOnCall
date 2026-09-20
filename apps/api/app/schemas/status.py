from pydantic import BaseModel

class DatabaseStatus(BaseModel):
    connected: bool
    details: str

class RedisStatus(BaseModel):
    connected: bool
    details: str

class SystemStatusResponse(BaseModel):
    service: str
    version: str
    environment: str
    status: str
    database: DatabaseStatus
    redis: RedisStatus
