"""SQLite persistence layer (SQLAlchemy ORM).

Stores chargeback records, prediction logs and evidence snapshots for the
dashboard and win/loss history. The database file lives at
data/chargebacks.db and tables are created on module import.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from utils.logger import get_logger

logger = get_logger()

PACKAGE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PACKAGE_DIR / "data" / "chargebacks.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ChargebackRecord(Base):
    __tablename__ = "chargeback_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chargeback_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    transaction_id: Mapped[str] = mapped_column(String)
    transaction_date: Mapped[datetime] = mapped_column(DateTime)
    amount_inr: Mapped[float] = mapped_column(Float)
    reason_code: Mapped[str] = mapped_column(String)
    merchant_name: Mapped[str] = mapped_column(String)
    customer_name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chargeback_id: Mapped[str] = mapped_column(
        String, ForeignKey("chargeback_records.chargeback_id"), index=True
    )
    win_probability: Mapped[float] = mapped_column(Float)
    recommendation: Mapped[str] = mapped_column(String)
    evidence_strength: Mapped[str] = mapped_column(String)
    evidence_completeness_score: Mapped[float] = mapped_column(Float)
    actual_outcome: Mapped[int | None] = mapped_column(Integer, nullable=True)
    false_positive_cost_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    letter_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class EvidenceSnapshot(Base):
    __tablename__ = "evidence_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chargeback_id: Mapped[str] = mapped_column(String, index=True)
    is_3ds_verified: Mapped[bool] = mapped_column(Boolean)
    avs_match: Mapped[bool] = mapped_column(Boolean)
    cvv_match: Mapped[bool] = mapped_column(Boolean)
    has_delivery_confirmation: Mapped[bool] = mapped_column(Boolean)
    has_signed_receipt: Mapped[bool] = mapped_column(Boolean)
    has_login_after_purchase: Mapped[bool] = mapped_column(Boolean)
    has_support_interaction: Mapped[bool] = mapped_column(Boolean)
    order_confirmation_sent: Mapped[bool] = mapped_column(Boolean)
    refund_policy_acknowledged: Mapped[bool] = mapped_column(Boolean)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DatabaseManager:
    """High-level CRUD + analytics facade over the SQLite database."""

    def __init__(self, db_url: str | None = None) -> None:
        self.engine = create_engine(db_url or DATABASE_URL, echo=False, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def init_db(self) -> None:
        Base.metadata.create_all(self.engine)
        logger.debug("Database initialised at {}", DB_PATH)

    # --------------------------------------------------------------- writes

    def insert_chargeback(self, data_dict: dict[str, Any]) -> ChargebackRecord:
        record = ChargebackRecord(**data_dict)
        with Session(self.engine) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
        logger.info("Chargeback inserted: {}", record.chargeback_id)
        return record

    def log_prediction(self, data_dict: dict[str, Any]) -> PredictionLog:
        entry = PredictionLog(**data_dict)
        with Session(self.engine) as session:
            session.add(entry)
            session.commit()
            session.refresh(entry)
        logger.info(
            "Prediction logged: {} -> {} (p={:.2f})",
            entry.chargeback_id,
            entry.recommendation,
            entry.win_probability,
        )
        return entry

    def save_evidence(self, data_dict: dict[str, Any]) -> EvidenceSnapshot:
        snapshot = EvidenceSnapshot(**data_dict)
        with Session(self.engine) as session:
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
        logger.debug("Evidence snapshot saved: {}", snapshot.chargeback_id)
        return snapshot

    # ---------------------------------------------------------------- reads

    def get_all_predictions(self) -> list[dict[str, Any]]:
        stmt = (
            select(PredictionLog, ChargebackRecord)
            .join(
                ChargebackRecord,
                PredictionLog.chargeback_id == ChargebackRecord.chargeback_id,
                isouter=True,
            )
            .order_by(PredictionLog.predicted_at.desc())
        )
        rows: list[dict[str, Any]] = []
        with Session(self.engine) as session:
            for pred, rec in session.execute(stmt):
                row = {
                    col: getattr(pred, col)
                    for col in PredictionLog.__table__.columns.keys()
                }
                if rec is not None:
                    row.update(
                        {
                            "amount_inr": rec.amount_inr,
                            "reason_code": rec.reason_code,
                            "merchant_name": rec.merchant_name,
                            "customer_name": rec.customer_name,
                        }
                    )
                rows.append(row)
        return rows

    def get_metrics_summary(self) -> dict[str, Any]:
        with Session(self.engine) as session:
            total_fought = session.execute(
                select(func.count())
                .select_from(PredictionLog)
                .where(PredictionLog.recommendation == "FIGHT")
            ).scalar_one()
            total_skipped = session.execute(
                select(func.count())
                .select_from(PredictionLog)
                .where(PredictionLog.recommendation == "SKIP")
            ).scalar_one()
            fought_known = session.execute(
                select(PredictionLog.actual_outcome).where(
                    PredictionLog.recommendation == "FIGHT",
                    PredictionLog.actual_outcome.is_not(None),
                )
            ).scalars().all()

        known_n = len(fought_known)
        wins = sum(1 for o in fought_known if o == 1)
        false_positives = known_n - wins
        win_rate = wins / known_n if known_n else 0.0
        fp_rate = false_positives / known_n if known_n else 0.0

        return {
            "win_rate": round(win_rate, 4),
            "fp_rate": round(fp_rate, 4),
            "total_fought": int(total_fought),
            "total_skipped": int(total_skipped),
            "fought_with_known_outcome": known_n,
        }


db_manager = DatabaseManager()
db_manager.init_db()


if __name__ == "__main__":
    mgr = DatabaseManager()
    mgr.init_db()
    summary = mgr.get_metrics_summary()
    print(f"Database ready at {DB_PATH}")
    print(f"Current metrics summary: {summary}")
