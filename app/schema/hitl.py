from enum import Enum
from pydantic import BaseModel, Field


class HITLStatus(str, Enum):
    PENDING_CLARIFICATION = "pending_clarification"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    EXPIRED = "expired"


class HITLResponse(BaseModel):
    status: HITLStatus
    request_id: str | None = None
    message: str
    result: str | None = None
    clarification_question: str | None = None


class HITLDecisionRequest(BaseModel):
    decision: str = Field(
        pattern="^(approve|reject)$"
    )
    comment: str | None = None


class HITLClarificationRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=200)