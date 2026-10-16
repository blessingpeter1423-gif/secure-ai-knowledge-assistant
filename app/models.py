import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import relationship

from app.database import Base


class Tenant(Base):

    __tablename__ = "tenants"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    tenant_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    users = relationship(
        "User",
        back_populates="tenant"
    )

    documents = relationship(
        "Document",
        back_populates="tenant"
    )

    audit_logs = relationship(
        "AuditLog",
        back_populates="tenant"
    )

    usage_events = relationship(
        "UsageEvent",
        back_populates="tenant"
    )


class Role(Base):

    __tablename__ = "roles"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        unique=True,
        nullable=False
    )

    users = relationship(
        "User",
        back_populates="role"
    )


class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        String,
        unique=True,
        nullable=False
    )

    username = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    password_hash = Column(
        String,
        nullable=False
    )

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id"),
        nullable=False
    )

    role_id = Column(
        Integer,
        ForeignKey("roles.id"),
        nullable=False
    )

    tenant = relationship(
        "Tenant",
        back_populates="users"
    )

    role = relationship(
        "Role",
        back_populates="users"
    )

    documents = relationship(
        "Document",
        back_populates="uploaded_by_user"
    )

    audit_logs = relationship(
        "AuditLog",
        back_populates="user"
    )

    usage_events = relationship(
        "UsageEvent",
        back_populates="user"
    )


class Document(Base):

    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )
    document_uuid = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4())
    )
    content_hash = Column(
        String(64),
        nullable=False,
        index=True
    )

    filename = Column(
        String,
        nullable=False
    )

    file_path = Column(
        String,
        nullable=False
    )

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )

    uploaded_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    access_level = Column(
        String,
        nullable=False,
        default="employee"
    )

    chunks_stored = Column(
        Integer,
        nullable=False,
        default=0
    )

    status = Column(
        String,
        nullable=False,
        default="indexed"
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    tenant = relationship(
        "Tenant",
        back_populates="documents"
    )

    uploaded_by_user = relationship(
        "User",
        back_populates="documents"
    )


class AuditLog(Base):

    __tablename__ = "audit_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    action = Column(
        String,
        nullable=False,
        index=True
    )

    resource_type = Column(
        String,
        nullable=True
    )

    resource_id = Column(
        String,
        nullable=True
    )

    status = Column(
        String,
        nullable=False,
        default="success"
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    tenant = relationship(
        "Tenant",
        back_populates="audit_logs"
    )

    user = relationship(
        "User",
        back_populates="audit_logs"
    )


class UsageEvent(Base):

    __tablename__ = "usage_events"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id"),
        nullable=False,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    event_type = Column(
        String,
        nullable=False,
        index=True
    )

    quantity = Column(
        Integer,
        nullable=False,
        default=1
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    tenant = relationship(
        "Tenant",
        back_populates="usage_events"
    )

    user = relationship(
        "User",
        back_populates="usage_events"
    )