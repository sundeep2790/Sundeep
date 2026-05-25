import uuid
import datetime
from datetime import timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR
from datarescue.backend.database import Base

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value

class User(Base):
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    device_token = Column(String, unique=True, nullable=False)
    credit_balance = Column(Integer, default=0, nullable=False)
    is_lifetime = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc), onupdate=lambda: datetime.datetime.now(timezone.utc), nullable=False)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # 'purchase' | 'deduction' | 'refund' | 'lifetime'
    amount = Column(Integer, nullable=False)  # positive for purchase, negative for deduction
    stripe_session_id = Column(String, nullable=True)
    pack_id = Column(String, nullable=True)  # 'starter' | 'standard' | 'plus' | 'unlimited' | 'appsumo'
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc), nullable=False)
