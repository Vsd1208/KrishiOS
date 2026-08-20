"""Voice service orchestrating STT, normalization, Agent Runtime, localization, and TTS."""

from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID, uuid4
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext
from app.agents.crop_advisory_agent import CropAdvisoryAgent
from app.agents.execution.context import ExecutionContext
from app.agents.providers.llm import MockLocalLLMProvider
from app.agents.tools.knowledge_search import KnowledgeSearchTool
from app.agents.tools.vision_analysis import VisionAnalysisTool
from app.agents.vision_agent import VisionIntelligenceAgent
from app.config.settings import get_settings
from app.knowledge.embeddings.pipeline import EmbeddingPipeline
from app.knowledge.retrieval.service import RetrievalService
from app.knowledge.vectorstore.qdrant import QdrantVectorStore
from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline

from app.voice.models.audio import AudioRecord
from app.voice.models.transcript import SpeechTranscript
from app.voice.providers.mock_stt import MockSTTProvider
from app.voice.providers.mock_tts import MockTTSProvider
from app.voice.providers.stt_base import SpeechToTextProvider
from app.voice.providers.tts_base import TextToSpeechProvider
from app.voice.schemas.voice import VoiceQueryResponse
from app.voice.services.normalization import AgriculturalLanguageNormalizer
from app.voice.services.storage import AudioStorageService
from app.voice.services.validator import AudioValidator


class VoiceService:
    """Orchestrates multilingual voice query processing end-to-end."""

    def __init__(
        self,
        session: AsyncSession,
        stt_provider: SpeechToTextProvider | None = None,
        tts_provider: TextToSpeechProvider | None = None,
        normalizer: AgriculturalLanguageNormalizer | None = None,
        validator: AudioValidator | None = None,
        storage_service: AudioStorageService | None = None,
    ) -> None:
        self._session = session
        self._settings = get_settings()
        self._stt = stt_provider or MockSTTProvider()
        self._tts = tts_provider or MockTTSProvider()
        self._normalizer = normalizer or AgriculturalLanguageNormalizer()
        self._validator = validator or AudioValidator()
        self._storage = storage_service or AudioStorageService()

    async def process_voice_query(
        self,
        file_bytes: bytes,
        original_filename: str,
        content_type: str | None,
        auth: AuthContext,
        hint_language: str | None = None,
        analysis_id: int | None = None,
    ) -> VoiceQueryResponse:
        """Process an incoming voice query audio file through STT, normalization, Agent Runtime, localization, and TTS."""
        t0 = perf_counter()
        req_id = uuid4()

        # 1. Validation
        val_res = self._validator.validate(file_bytes, content_type)
        if not val_res.valid:
            raise ValueError(f"Audio validation failed: {', '.join(val_res.errors)}")

        # 2. SHA-256 Storage & Deduplication
        file_hash = self._storage.compute_hash(file_bytes)
        storage_path = await self._storage.save_audio(file_bytes, file_hash, original_filename)

        # 3. STT Transcription
        stt_res = await self._stt.transcribe(storage_path, hint_language=hint_language)

        # Handle low-confidence transcription explicitly without hallucination
        if stt_res.transcription_confidence < 0.4:
            logger.warning("VoiceService: low transcription confidence ({})", stt_res.transcription_confidence)
            # Create Audio Record & Transcript
            audio_rec = AudioRecord(
                owner_uuid=auth.user_uuid,
                file_hash=file_hash,
                storage_key=str(storage_path),
                original_filename=original_filename,
                mime_type=val_res.mime_type,
                file_size=val_res.file_size,
                duration_seconds=val_res.estimated_duration_seconds,
                language_detected=stt_res.detected_language,
                language_confidence=stt_res.language_confidence,
            )
            self._session.add(audio_rec)
            await self._session.commit()
            await self._session.refresh(audio_rec)

            transcript_rec = SpeechTranscript(
                audio_id=audio_rec.id,
                raw_transcript=stt_res.raw_transcript,
                detected_language=stt_res.detected_language,
                language_confidence=stt_res.language_confidence,
                transcription_confidence=stt_res.transcription_confidence,
                model_name=stt_res.model_name,
                model_version=stt_res.model_version,
            )
            self._session.add(transcript_rec)
            await self._session.commit()

            return VoiceQueryResponse(
                request_id=req_id,
                audio_id=audio_rec.id,
                audio_uuid=audio_rec.uuid,
                detected_language=stt_res.detected_language,
                raw_transcript=stt_res.raw_transcript,
                normalized_query=stt_res.raw_transcript,
                response_text="Voice audio clarity was low. Please speak closer to the microphone or try typing your question.",
                spoken_audio_reference=None,
                citations=[],
                confidence=stt_res.transcription_confidence,
                is_code_switched=stt_res.is_code_switched,
                processing_time_ms=(perf_counter() - t0) * 1000,
                agent_used="voice_validator",
            )

        # 4. Save DB Records
        audio_rec = AudioRecord(
            owner_uuid=auth.user_uuid,
            file_hash=file_hash,
            storage_key=str(storage_path),
            original_filename=original_filename,
            mime_type=val_res.mime_type,
            file_size=val_res.file_size,
            duration_seconds=val_res.estimated_duration_seconds,
            language_detected=stt_res.detected_language,
            language_confidence=stt_res.language_confidence,
        )
        self._session.add(audio_rec)
        await self._session.commit()
        await self._session.refresh(audio_rec)

        # 5. Agricultural Language Normalization & Terminology Mapping
        norm_res = self._normalizer.normalize(stt_res.raw_transcript, stt_res.detected_language)

        transcript_rec = SpeechTranscript(
            audio_id=audio_rec.id,
            raw_transcript=stt_res.raw_transcript,
            detected_language=stt_res.detected_language,
            language_confidence=stt_res.language_confidence,
            transcription_confidence=stt_res.transcription_confidence,
            model_name=stt_res.model_name,
            model_version=stt_res.model_version,
            normalized_query=norm_res.normalized_query,
            detected_intent="IMAGE_ANALYSIS" if analysis_id else "CROP_ADVISORY",
            extracted_entities=norm_res.extracted_entities,
        )
        self._session.add(transcript_rec)
        await self._session.commit()
        await self._session.refresh(transcript_rec)

        # 6. Execute Agent Runtime
        exec_ctx = ExecutionContext(
            execution_id=req_id,
            session_id=str(audio_rec.uuid),
            auth=auth,
            language=stt_res.detected_language,
            crop=norm_res.resolved_crop or "Paddy",
        )

        llm = MockLocalLLMProvider()
        vector_store = QdrantVectorStore(
            host=self._settings.QDRANT_HOST,
            port=self._settings.QDRANT_PORT,
            collection_name=self._settings.QDRANT_COLLECTION,
        )
        embedder = EmbeddingPipeline(
            model_name=self._settings.EMBEDDING_MODEL_NAME,
            model_version=self._settings.EMBEDDING_MODEL_VERSION,
        )
        retrieval_service = RetrievalService(
            session=self._session,
            vector_store=vector_store,
            embedding_pipeline=embedder,
        )
        retrieval_pipeline = EnterpriseRetrievalPipeline(retrieval_service=retrieval_service)
        search_tool = KnowledgeSearchTool(pipeline=retrieval_pipeline)

        if analysis_id is not None:
            # Voice + Image multimodal workflow
            from app.database.session import async_session_factory
            vision_tool = VisionAnalysisTool(session_factory=async_session_factory)
            agent = VisionIntelligenceAgent(llm_provider=llm, search_tool=search_tool, vision_tool=vision_tool)
            exec_res = await agent.execute(
                task=norm_res.raw_query,
                context=exec_ctx,
                parameters={"analysis_id": analysis_id},
            )
            agent_used = "vision_intelligence_agent"
        else:
            # Standard Voice query workflow
            agent = CropAdvisoryAgent(llm_provider=llm, search_tool=search_tool)
            exec_res = await agent.execute(
                task=norm_res.normalized_query,
                context=exec_ctx,
                parameters={"crop": norm_res.resolved_crop or "Paddy"},
            )
            agent_used = "crop_advisory_agent"

        raw_response_text = exec_res.output.get("recommendation", "Here is the advisory for your query.")
        citations = exec_res.citations

        # 7. Response Localization (preserve citations while localizing explanation)
        localized_text = self._localize_response(
            raw_text=raw_response_text,
            target_language=stt_res.detected_language,
            crop=norm_res.resolved_crop,
            disease=norm_res.resolved_disease,
        )

        # 8. TTS Synthesis
        tts_res = await self._tts.synthesize(text=localized_text, language=stt_res.detected_language)

        total_ms = (perf_counter() - t0) * 1000

        return VoiceQueryResponse(
            request_id=req_id,
            audio_id=audio_rec.id,
            audio_uuid=audio_rec.uuid,
            detected_language=stt_res.detected_language,
            raw_transcript=stt_res.raw_transcript,
            normalized_query=norm_res.normalized_query,
            response_text=localized_text,
            spoken_audio_reference=tts_res.audio_uuid,
            citations=citations,
            confidence=exec_res.confidence_score,
            is_code_switched=norm_res.is_code_switched,
            processing_time_ms=total_ms,
            agent_used=agent_used,
        )

    def _localize_response(
        self,
        raw_text: str,
        target_language: str,
        crop: str | None = None,
        disease: str | None = None,
    ) -> str:
        """Localize advisory explanation into target language while preserving source citations."""
        if target_language == "te":
            crop_name = crop or "వరి"
            dis_name = disease or "లక్షణాలు"
            return (
                f"మీ {crop_name} పంటకు సంబంధించి {dis_name} సమాచారం: "
                f"{raw_text} (వివరాలు సరిచూసుకోండి)."
            )
        elif target_language == "hi":
            crop_name = crop or "फसल"
            dis_name = disease or "लक्षणों"
            return (
                f"आपकी {crop_name} फसल के {dis_name} के संबंध में सलाह: "
                f"{raw_text} (प्रमाणित विवरण उपलब्ध हैं)।"
            )
        else:
            return raw_text
