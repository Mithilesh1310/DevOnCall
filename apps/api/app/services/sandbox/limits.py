import os
from pydantic import BaseModel

class SandboxLimits(BaseModel):
    cpu_limit: float = float(os.getenv("SANDBOX_CPU_LIMIT", "2.0"))
    memory_limit: str = os.getenv("SANDBOX_MEMORY_LIMIT", "1g")
    timeout_seconds: int = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "120"))
    max_output_bytes: int = int(os.getenv("SANDBOX_MAX_OUTPUT_BYTES", "2097152")) # 2 MB

default_sandbox_limits = SandboxLimits()
