"""Relational data via SQLAlchemy: employees (mock HRMS), HR tickets and chat history.

DATABASE_URL decides the engine: SQLite locally, PostgreSQL in docker-compose / Kubernetes.
Storing chat history here (instead of in process memory) keeps the API
*stateless*, so any replica behind a load balancer can serve any request.
"""
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(50))
    earned_leave: Mapped[float] = mapped_column()
    sick_leave: Mapped[float] = mapped_column()
    casual_leave: Mapped[float] = mapped_column()
    hrbp: Mapped[str] = mapped_column(String(100))


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"))
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(10))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


SEED_EMPLOYEES = [
    Employee(id="E1001", name="Ananya Rao", department="Engineering", earned_leave=14, sick_leave=9, casual_leave=4, hrbp="Priya Menon"),
    Employee(id="E1002", name="Rahul Verma", department="Sales", earned_leave=6.5, sick_leave=12, casual_leave=2, hrbp="Karthik Iyer"),
    Employee(id="E1003", name="Fatima Khan", department="Finance", earned_leave=21, sick_leave=5, casual_leave=6, hrbp="Priya Menon"),
]

_engine = None
_SessionLocal: sessionmaker | None = None


def init_db(url: str | None = None) -> None:
    global _engine, _SessionLocal
    url = url or get_settings().database_url
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:memory:"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(url, pool_pre_ping=True)
    _SessionLocal = sessionmaker(_engine, expire_on_commit=False)
    Base.metadata.create_all(_engine)
    with _SessionLocal() as s:
        if not s.scalar(select(Employee).limit(1)):
            s.add_all([Employee(**{c.name: getattr(e, c.name) for c in Employee.__table__.columns}) for e in SEED_EMPLOYEES])
            s.commit()


def session() -> Session:
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()


def ping() -> bool:
    with session() as s:
        s.execute(select(1))
    return True


def get_employee(employee_id: str) -> Employee | None:
    with session() as s:
        return s.get(Employee, employee_id)


def create_ticket(employee_id: str, question: str) -> int:
    with session() as s:
        t = Ticket(employee_id=employee_id, question=question)
        s.add(t)
        s.commit()
        return t.id


def list_tickets(employee_id: str | None = None) -> list[Ticket]:
    with session() as s:
        q = select(Ticket).order_by(Ticket.id.desc())
        if employee_id:
            q = q.where(Ticket.employee_id == employee_id)
        return list(s.scalars(q))


def save_message(session_id: str, role: str, content: str) -> None:
    with session() as s:
        s.add(ChatMessage(session_id=session_id, role=role, content=content))
        s.commit()


def load_history(session_id: str, limit: int) -> list[ChatMessage]:
    with session() as s:
        rows = s.scalars(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id.desc()).limit(limit)
        )
        return list(reversed(list(rows)))
