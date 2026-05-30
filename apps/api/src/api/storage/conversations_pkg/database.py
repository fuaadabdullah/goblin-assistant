from datetime import datetime
from typing import Any, Dict, List, Optional
import os
import uuid

import structlog
from sqlalchemy import delete, desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from .base import ConversationStore
from .models import Conversation, ConversationMessage

logger = structlog.get_logger()

try:
    from ..models import ConversationModel, MessageModel
    from ..database import get_db_context, init_db
except ImportError:
    pass


class DatabaseConversationStore(ConversationStore):
    """Database-backed conversation storage for production."""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv("DATABASE_URL")

    async def _ensure_initialized(self):
        await init_db()

    async def save_conversation(self, conversation: Conversation) -> None:
        try:
            async with get_db_context() as session:
                result = await session.execute(
                    select(ConversationModel).where(
                        ConversationModel.conversation_id == conversation.conversation_id
                    )
                )
                db_conversation = result.scalar_one_or_none()

                if not db_conversation:
                    db_conversation = ConversationModel(
                        conversation_id=conversation.conversation_id,
                        user_id=conversation.user_id,
                        title=conversation.title,
                        created_at=conversation.created_at,
                        updated_at=conversation.updated_at,
                        metadata_=conversation.metadata,
                    )
                    session.add(db_conversation)
                else:
                    db_conversation.title = conversation.title
                    db_conversation.updated_at = conversation.updated_at
                    db_conversation.metadata_ = conversation.metadata

                await session.flush()

                for msg in conversation.messages:
                    msg_result = await session.execute(
                        select(MessageModel).where(MessageModel.message_id == msg.message_id)
                    )
                    db_msg = msg_result.scalar_one_or_none()
                    if not db_msg:
                        session.add(
                            MessageModel(
                                message_id=msg.message_id,
                                conversation_id=conversation.conversation_id,
                                role=msg.role,
                                content=msg.content,
                                timestamp=msg.timestamp,
                                metadata_=msg.metadata,
                            )
                        )
        except SQLAlchemyError as exc:
            logger.error(
                "db_write_failed",
                operation="save_conversation",
                conversation_id=conversation.conversation_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        try:
            async with get_db_context() as session:
                result = await session.execute(
                    select(ConversationModel)
                    .where(ConversationModel.conversation_id == conversation_id)
                    .options(selectinload(ConversationModel.messages))
                )
                db_conversation = result.scalar_one_or_none()
                if not db_conversation:
                    return None

                messages = [
                    ConversationMessage(
                        role=msg.role,
                        content=msg.content,
                        message_id=msg.message_id,
                        timestamp=msg.timestamp,
                        metadata=msg.metadata_,
                    )
                    for msg in sorted(db_conversation.messages, key=lambda item: item.timestamp)
                ]

                return Conversation(
                    conversation_id=db_conversation.conversation_id,
                    user_id=db_conversation.user_id,
                    title=db_conversation.title,
                    messages=messages,
                    created_at=db_conversation.created_at,
                    updated_at=db_conversation.updated_at,
                    metadata=db_conversation.metadata_,
                )
        except SQLAlchemyError as exc:
            logger.error(
                "db_read_failed",
                operation="get_conversation",
                conversation_id=conversation_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

    async def delete_conversation(self, conversation_id: str) -> bool:
        async with get_db_context() as session:
            result = await session.execute(
                delete(ConversationModel).where(
                    ConversationModel.conversation_id == conversation_id
                )
            )
            return result.rowcount > 0

    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Conversation]:
        async with get_db_context() as session:
            query = select(ConversationModel).order_by(desc(ConversationModel.updated_at))
            if user_id:
                query = query.where(ConversationModel.user_id == user_id)

            query = query.limit(limit).options(selectinload(ConversationModel.messages))
            result = await session.execute(query)
            db_conversations = result.scalars().all()

            conversations = []
            for db_conv in db_conversations:
                messages = [
                    ConversationMessage(
                        role=msg.role,
                        content=msg.content,
                        message_id=msg.message_id,
                        timestamp=msg.timestamp,
                        metadata=msg.metadata_,
                    )
                    for msg in sorted(db_conv.messages, key=lambda item: item.timestamp)
                ]

                conversations.append(
                    Conversation(
                        conversation_id=db_conv.conversation_id,
                        user_id=db_conv.user_id,
                        title=db_conv.title,
                        messages=messages,
                        created_at=db_conv.created_at,
                        updated_at=db_conv.updated_at,
                        metadata=db_conv.metadata_,
                    )
                )

            return conversations

    async def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        async with get_db_context() as session:
            result = await session.execute(
                select(ConversationModel).where(
                    ConversationModel.conversation_id == conversation_id
                )
            )
            db_conversation = result.scalar_one_or_none()
            if db_conversation:
                db_conversation.title = title
                db_conversation.updated_at = datetime.utcnow()
                return True
            return False

    async def archive_messages(
        self,
        conversation_id: str,
        message_ids: List[str],
        summary_content: str,
        summary_metadata: Optional[Dict[str, Any]] = None,
        summary_message_id: Optional[str] = None,
        summary_timestamp: Optional[datetime] = None,
    ) -> bool:
        if not message_ids:
            return False

        from ..models import MessageAttachmentModel

        try:
            async with get_db_context() as session:
                conv_result = await session.execute(
                    select(ConversationModel).where(
                        ConversationModel.conversation_id == conversation_id
                    )
                )
                db_conversation = conv_result.scalar_one_or_none()
                if not db_conversation:
                    return False

                archived_result = await session.execute(
                    select(MessageModel).where(
                        MessageModel.conversation_id == conversation_id,
                        MessageModel.message_id.in_(message_ids),
                    )
                )
                archived_messages = archived_result.scalars().all()
                if not archived_messages:
                    return False

                summary_ts = summary_timestamp or max(msg.timestamp for msg in archived_messages)
                archive_ids = [msg.message_id for msg in archived_messages]

                await session.execute(
                    delete(MessageAttachmentModel).where(
                        MessageAttachmentModel.message_id.in_(archive_ids)
                    )
                )
                await session.execute(
                    delete(MessageModel).where(
                        MessageModel.conversation_id == conversation_id,
                        MessageModel.message_id.in_(archive_ids),
                    )
                )

                session.add(
                    MessageModel(
                        message_id=summary_message_id or str(uuid.uuid4()),
                        conversation_id=conversation_id,
                        role="system",
                        content=summary_content,
                        timestamp=summary_ts,
                        metadata_=summary_metadata or {},
                    )
                )

                db_conversation.updated_at = max(
                    db_conversation.updated_at or summary_ts,
                    summary_ts,
                )
                return True
        except SQLAlchemyError as exc:
            logger.error(
                "db_write_failed",
                operation="archive_messages",
                conversation_id=conversation_id,
                message_count=len(message_ids),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

    async def check_conversation_owner(
        self,
        conversation_id: str,
        user_id: str,
        db=None,
    ) -> bool:
        async def _run(session) -> bool:
            result = await session.execute(
                select(ConversationModel.user_id).where(
                    ConversationModel.conversation_id == conversation_id
                )
            )
            row = result.scalar_one_or_none()
            return row == user_id

        if db is not None:
            return await _run(db)
        async with get_db_context() as session:
            return await _run(session)
