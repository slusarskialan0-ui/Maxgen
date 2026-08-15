from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Industry(Base):
    __tablename__ = "industries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, default="")
    service_type = Column(String, default="")
    clients = relationship("Client", back_populates="industry_rel")


class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, index=True)
    voivodeship = Column(String, index=True, nullable=False)
    county = Column(String, default="")
    city = Column(String, default="")
    clients = relationship("Client", back_populates="location_rel")


class VoivodeshipStatus(Base):
    __tablename__ = "voivodeship_statuses"
    id = Column(Integer, primary_key=True, index=True)
    voivodeship = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="nie_rozpoczete")
    priority = Column(Integer, default=0)
    last_scan = Column(DateTime, nullable=True)
    clients_count = Column(Integer, default=0)
    orders_count = Column(Integer, default=0)
    error_message = Column(Text, default="")


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, default="default")
    company_name = Column(String, index=True, nullable=False)
    industry = Column(String, index=True, nullable=False)
    industry_id = Column(Integer, ForeignKey("industries.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    voivodeship = Column(String, index=True, default="")
    county = Column(String, default="")
    city = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    website = Column(String, default="")
    source_type = Column(String, default="")
    source_detail = Column(String, default="")
    acquired_at = Column(DateTime, default=func.now())
    status = Column(String, default="nowy")

    industry_rel = relationship("Industry", back_populates="clients")
    location_rel = relationship("Location", back_populates="clients")
    orders = relationship("Order", back_populates="client")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, default="default")
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    value = Column(Float, default=0.0)
    status = Column(String, default="nowe")
    created_at = Column(DateTime, default=func.now())

    client = relationship("Client", back_populates="orders")
    history = relationship("OrderHistory", back_populates="order")


class OrderHistory(Base):
    __tablename__ = "order_history"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    note = Column(Text, default="")
    status_change = Column(String, default="")
    created_at = Column(DateTime, default=func.now())

    order = relationship("Order", back_populates="history")


class AcquisitionLog(Base):
    __tablename__ = "acquisition_logs"
    id = Column(Integer, primary_key=True, index=True)
    voivodeship = Column(String, index=True)
    industries = Column(String)
    source_type = Column(String)
    found = Column(Integer, default=0)
    accepted = Column(Integer, default=0)
    rejected = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, index=True, nullable=False)
    ip = Column(String, index=True, default="")
    user_agent = Column(String, default="")
    endpoint = Column(String, index=True, default="")
    ts = Column(DateTime, default=func.now(), nullable=False)


class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, default="default")
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="aktywna")
    source = Column(String, default="")
    budget = Column(Float, default=0.0)
    target_leads = Column(Integer, default=0)
    current_leads = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())
    leads = relationship("Lead", back_populates="campaign")


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, default="default")
    full_name = Column(String, default="")
    email = Column(String, index=True, default="")
    phone = Column(String, default="")
    company = Column(String, default="")
    industry = Column(String, index=True, default="")
    voivodeship = Column(String, index=True, default="")
    source = Column(String, default="")
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    assigned_to = Column(String, default="")
    stage = Column(String, default="nowy")
    score = Column(Float, default=0.0)
    conversion_probability = Column(Float, default=0.0)
    notes = Column(Text, default="")
    tags = Column(String, default="")
    follow_up_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    campaign = relationship("Campaign", back_populates="leads")
    offers = relationship("Offer", back_populates="lead")
    payments = relationship("Payment", back_populates="lead")


class SourceConfig(Base):
    __tablename__ = "sources_config"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    source_type = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)
    config_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=func.now())


class Automation(Base):
    __tablename__ = "automations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    trigger = Column(String, default="")
    action = Column(String, default="")
    condition_json = Column(Text, default="{}")
    enabled = Column(Boolean, default=True)
    runs = Column(Integer, default=0)
    last_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())


class UserProfile(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String, default="")
    role = Column(String, default="agent")
    email = Column(String, default="")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class Offer(Base):
    __tablename__ = "offers"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, default="")
    amount = Column(Float, default=0.0)
    status = Column(String, default="draft")  # draft, sent, accepted, rejected
    generated_offline = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    lead = relationship("Lead", back_populates="offers")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=True)
    amount = Column(Float, default=0.0)
    status = Column(String, default="pending")  # pending, confirmed, failed, refunded
    method = Column(String, default="offline_transfer")
    confirmation_code = Column(String, default="")
    log = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    lead = relationship("Lead", back_populates="payments")


class EngineLog(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, default="info")
    module = Column(String, default="engine")
    message = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())


class EngineEvent(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True, default="")
    payload_json = Column(Text, default="{}")
    source = Column(String, default="offline")
    created_at = Column(DateTime, default=func.now())


class BackupRecord(Base):
    __tablename__ = "backups"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    size_bytes = Column(Integer, default=0)
    status = Column(String, default="ok")
    created_at = Column(DateTime, default=func.now())
