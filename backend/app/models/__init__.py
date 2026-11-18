"""SQLAlchemy ORM models for the KrishiOS domain.

Sprint 0 / Sprint 1 — Domain models
Sprint 2            — Knowledge infrastructure models
"""

from app.models.crop_catalog import CropCatalogEntry
from app.models.translation import TranslationRecord
from app.models.conversation import ConversationTurnRecord
from app.models.extension import ExtensionAssignment
from app.models.feedback import AnswerFeedback
from app.models.media import MediaAsset
from app.models.govconnect import (
    BulletinDelivery,
    BulletinTranslation,
    DistrictWeatherSnapshot,
    FarmerLocation,
    GovConnectAudit,
    GovtBulletin,
    GrievanceEvent,
    GrievanceTicket,
    MandiPriceDaily,
    PushSubscription,
    SchemeEntry,
)
from app.models.forecasting import ForecastImport, YieldForecastRecord
from app.models.surveillance import DiagnosisReport
from app.models.crop import Crop
from app.models.district import District
from app.models.document_chunk import DocumentChunk
from app.models.farmer import Farmer
from app.models.field import Field
from app.models.field_crop import FieldCrop, FieldCropStatus
from app.models.knowledge_document import DocumentStatus, KnowledgeDocument
from app.models.officer import Officer
from app.models.retrieval_index import (
    IndexedDocumentState,
    RetrievalBuildMode,
    RetrievalIndexKind,
    RetrievalIndexStatus,
    RetrievalIndexVersion,
)
from app.models.soil_sample import SoilSample, SoilSampleStatus
from app.models.user import RefreshToken, User
from app.models.graph_candidate import GraphKnowledgeCandidate
from app.vision.models.image import CropImage
from app.vision.models.analysis import ImageAnalysis
from app.voice.models.audio import AudioRecord
from app.voice.models.transcript import SpeechTranscript

from app.models.proactive import (
    AlertNotificationRecord,
    AlertPriority,
    AlertStatus,
    NotificationChannel,
    NotificationPreferenceRecord,
    ProactiveDecisionRecord,
    ProactiveEventRecord,
    RiskSeverity,
)

__all__ = [
    # Sprint 0/1 — domain
    "Crop",
    "District",
    "Farmer",
    "Field",
    "FieldCrop",
    "FieldCropStatus",
    "Officer",
    "SoilSample",
    "SoilSampleStatus",
    # Sprint 2 — knowledge
    "DocumentChunk",
    "DocumentStatus",
    "IndexedDocumentState",
    "KnowledgeDocument",
    "RetrievalBuildMode",
    "RetrievalIndexKind",
    "RetrievalIndexStatus",
    "RetrievalIndexVersion",
    "GraphKnowledgeCandidate",
    # Sprint 5 — Identity
    "RefreshToken",
    "User",
    # Sprint 7 — Vision
    "CropImage",
    "ImageAnalysis",
    # Sprint 8 — Voice
    "AudioRecord",
    "SpeechTranscript",
    # Sprint 10 — Proactive Intelligence
    "AlertNotificationRecord",
    "AlertPriority",
    "AlertStatus",
    "NotificationChannel",
    "NotificationPreferenceRecord",
    "ProactiveDecisionRecord",
    "ProactiveEventRecord",
    "RiskSeverity",
    # Sprint 11 — catalog, translation, conversation, assisted mode, feedback, media
    "AnswerFeedback",
    "ConversationTurnRecord",
    "CropCatalogEntry",
    "ExtensionAssignment",
    "MediaAsset",
    "TranslationRecord",
    # Sprint 11, Phase 4 — Govt Connect, locations (F2), grievances and schemes (F4)
    "BulletinDelivery",
    "BulletinTranslation",
    "DistrictWeatherSnapshot",
    "FarmerLocation",
    "GovConnectAudit",
    "GovtBulletin",
    "GrievanceEvent",
    "GrievanceTicket",
    "MandiPriceDaily",
    "ForecastImport",
    "YieldForecastRecord",
    "DiagnosisReport",
    "PushSubscription",
    "SchemeEntry",
]
