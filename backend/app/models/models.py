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
    status = Column(String, default="nie_rozpoczete")  # nie_rozpoczete, w_trakcie, zakonczone, ponowny_skan
    priority = Column(Integer, default=0)
    last_scan = Column(DateTime, nullable=True)
    clients_count = Column(Integer, default=0)
    orders_count = Column(Integer, default=0)
    error_message = Column(Text, default="")


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, default="default")  # developer platform foundation
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
    source_type = Column(String, default="")  # katalog, mapa, rejestr, social, ogloszenia
    source_detail = Column(String, default="")
    acquired_at = Column(DateTime, default=func.now())
    status = Column(String, default="nowy")  # nowy, zweryfikowany, odrzucony

    industry_rel = relationship("Industry", back_populates="clients")
    location_rel = relationship("Location", back_populates="clients")
    orders = relationship("Order", back_populates="client")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, default="default")  # developer platform foundation
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    value = Column(Float, default=0.0)
    status = Column(String, default="nowe")  # nowe, do_kontaktu, w_trakcie, zakonczone
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
    industries = Column(String)  # comma-separated
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



class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default="sales")
    territory = Column(String, default="Polska")
    capacity = Column(Integer, default=25)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, default="default")
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, default="")
    source = Column(String, default="")
    channel = Column(String, default="offline")
    audience = Column(String, default="")
    cta = Column(String, default="")
    ad_copy = Column(Text, default="")
    traffic_goal = Column(Integer, default=0)
    budget = Column(Float, default=0.0)
    target_leads = Column(Integer, default=0)
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=func.now())
    generated_at = Column(DateTime, default=func.now())


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, default="default")
    # New leads router fields
    full_name = Column(String, default="")
    company = Column(String, index=True, default="")
    source = Column(String, index=True, default="offline")
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    assigned_to = Column(String, index=True, default="")
    stage = Column(String, index=True, default="nowy")
    score = Column(Float, default=0.0)
    conversion_probability = Column(Float, default=0.0)
    tags = Column(String, default="")
    follow_up_at = Column(DateTime, nullable=True)
    # Old auto_ops router fields (kept for backward compatibility)
    company_name = Column(String, index=True, default="")
    source_type = Column(String, index=True, default="offline")
    traffic_score = Column(Integer, default=0)
    offline_ai_score = Column(Integer, default=0)
    qualification_status = Column(String, default="new")
    funnel_stage = Column(String, default="generated")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    campaign_name = Column(String, default="")
    generated_content = Column(Text, default="")
    follow_up_due_at = Column(DateTime, nullable=True)
    is_closed = Column(Boolean, default=False)
    # Shared fields
    industry = Column(String, index=True, default="")
    voivodeship = Column(String, index=True, default="")
    city = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    website = Column(String, default="")
    notes = Column(Text, default="")
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())



class Offer(Base):
    __tablename__ = "offers"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, default="default")
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    amount = Column(Float, default=0.0)
    currency = Column(String, default="PLN")
    status = Column(String, default="draft")
    sent_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    # Old auto_ops fields kept for backward compatibility
    summary = Column(Text, default="")
    price = Column(Float, default=0.0)
    sales_copy = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, index=True, default="default")
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=True)
    amount = Column(Float, default=0.0)
    currency = Column(String, default="PLN")
    status = Column(String, default="pending")
    method = Column(String, default="offline_transfer")
    confirmation_code = Column(String, default="")
    note = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())
    confirmed_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)


class PaymentLog(Base):
    __tablename__ = "payment_logs"
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    action = Column(String, nullable=False)
    details = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())


class BackupRecord(Base):
    __tablename__ = "backup_records"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    size_bytes = Column(Integer, default=0)
    status = Column(String, default="ok")
    created_at = Column(DateTime, default=func.now())


class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, index=True, nullable=False)
    message = Column(Text, default="")
    metadata_text = Column(Text, default="")
    created_at = Column(DateTime, default=func.now())


class Automation(Base):
    __tablename__ = "automations"
    id = Column(Integer, primary_key=True, index=True)
    # Fields used by automations router (workflow rules)
    name = Column(String, index=True, nullable=False, default="")
    trigger = Column(String, index=True, default="new_lead")
    action = Column(String, default="assign")
    condition_json = Column(Text, default="{}")
    enabled = Column(Boolean, default=True)
    runs = Column(Integer, default=0)
    last_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    # Fields used by auto_ops router (background job tracking)
    automation_type = Column(String, index=True, default="")
    status = Column(String, default="idle")
    items_processed = Column(Integer, default=0)
    summary = Column(Text, default="")
    recovery_action = Column(String, default="")
    last_run_at = Column(DateTime, nullable=True)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, default="")
    role = Column(String, default="agent")  # agent, manager, admin
    email = Column(String, default="")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class SystemConfig(Base):
    """Dynamic runtime configuration stored in DB — no server restart needed."""
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SocialChannelEvent(Base):
    """Rejestruje każde kliknięcie/aktywację kanału social media."""
    __tablename__ = "social_channel_events"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, index=True, nullable=False)   # np. telegram_chat, facebook_messenger
    target_url = Column(Text, default="")
    params_json = Column(Text, default="{}")                 # JSON z parametrami użytymi do generacji linku
    ip = Column(String, default="")
    user_agent = Column(String, default="")
    created_at = Column(DateTime, default=func.now())


class B2BLead(Base):
    """Scraped B2B order/commission leads from external platforms (OLX, Useme, Oferteo)."""
    __tablename__ = "b2b_leads"
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True, default="")
    title = Column(String, nullable=False, default="")
    budget = Column(Float, nullable=True)
    fvat_required = Column(Boolean, default=False)
    description = Column(Text, default="")
    contact_info = Column(Text, default="")   # JSON: {phones: [], emails: []}
    score = Column(Integer, default=0)         # 1-100 LeadScore
    url = Column(String, default="")
    source = Column(String, index=True, default="")  # olx | useme | oferteo
    content_hash = Column(String, index=True, default="")  # SHA256 for dedup
    sent_to_telegram = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
