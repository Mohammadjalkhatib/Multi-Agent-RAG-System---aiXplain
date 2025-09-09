"""
Purpose: Centralize configuration
Ultimate goal: load secrets & asset IDs from .env using Pydantic v2 style.
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    AIXPLAIN_API_KEY: str = Field(..., description="aiXplain API key (env var AIXPLAIN_API_KEY)")

    # Fixed IDs (we only integrate with your existing assets)
    LLM_ID: str = "669a63646eb56306647e1091"
    AGENT_POLICY_TEAM: str = "68bc1ef5def19d770c2603d5"
    AGENT_KNOWLEDGE_ASSISTANT: str = "68bc1ae7def19d770c26023b"
    AGENT_POLICY_NAVIGATOR: str = "68bc1d7fdef19d770c26038f"

    TOOL_KNOWLEDGE_INDEX: str = "68be93e3d4e0b5e6e1fdaf8b"
    TOOL_FIND: str = "68bc1be12c12f9d53ce1e7a8"
    TOOL_PDF_EXTRACTOR: str = "68bc1bc82c12f9d53ce1e79a"

    INDEX_ID: str = "68bd86666e7528eb1aa6f237"
    PIPELINE_EXEC_ORDER_RETRIEVAL: str = "68bc1d45def19d770c260355"

    PIPELINE_QUESTION_KEY: str = Field(default="question")
    PIPELINE_INDEX_KEY: str = Field(default="index_id")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

# ...
LLM_ID: str = "669a63646eb56306647e1091"  # default GPT-4o Mini you had
# You can override in .env like: LLM_ID=6895d70ed50c89537c1cf238

settings = Settings()
