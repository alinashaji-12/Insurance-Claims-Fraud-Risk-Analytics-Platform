"""
Seed SQLite from backend/data/raw/claims.csv.

Expects the Kaggle / Oracle vehicle claim fraud dataset
(https://www.kaggle.com/datasets/shivamb/vehicle-claim-fraud-detection)
with columns including PolicyNumber, FraudFound_P, BasePolicy, etc.

Fails loudly if the file is missing or required columns are absent.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select, text

from app.core.database import SessionLocal, engine, init_db
from app.models.claim import Claim

RAW_CSV = Path(__file__).resolve().parent.parent / "data" / "raw" / "claims.csv"
DEMO_CSV = Path(__file__).resolve().parent.parent / "data" / "demo" / "claims_demo.csv"

# Simple analyst CSV (bulk upload / committed demo seed)
SIMPLE_REQUIRED = {
    "policy_number",
    "claimant_name",
    "claimant_phone",
    "claimant_address",
    "bank_account",
    "vehicle_vin",
    "incident_date",
    "claim_type",
    "claim_amount",
    "repair_shop",
}

# Required columns for the vehicle insurance fraud dataset (Oracle / Kaggle)
REQUIRED_COLUMNS = {
    "PolicyNumber",
    "FraudFound_P",
    "BasePolicy",
    "VehiclePrice",
    "Make",
    "AccidentArea",
    "Fault",
    "Age",
    "Sex",
    "Month",
    "Year",
    "MonthClaimed",
    "DayOfWeekClaimed",
    "WeekOfMonthClaimed",
    "VehicleCategory",
    "PastNumberOfClaims",
    "AgeOfVehicle",
    "PoliceReportFiled",
    "WitnessPresent",
    "Days_Policy_Claim",
    "AddressChange_Claim",
    "Deductible",
    "DriverRating",
    "PolicyType",
}

MONTH_MAP = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

# Midpoint estimates for categorical VehiclePrice bands → claim amount proxy
VEHICLE_PRICE_MIDPOINTS = {
    "less than 20000": 15000.0,
    "20000 to 29000": 24500.0,
    "30000 to 39000": 34500.0,
    "40000 to 59000": 49500.0,
    "60000 to 69000": 64500.0,
    "more than 69000": 85000.0,
}

FIRST_NAMES = [
    "Alex",
    "Jordan",
    "Sam",
    "Taylor",
    "Morgan",
    "Casey",
    "Riley",
    "Avery",
    "Quinn",
    "Jamie",
    "Cameron",
    "Drew",
    "Harper",
    "Logan",
    "Reese",
]
LAST_NAMES = [
    "Nguyen",
    "Patel",
    "Garcia",
    "Smith",
    "Johnson",
    "Kim",
    "Brown",
    "Davis",
    "Martinez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Lee",
    "White",
    "Harris",
]
CITIES = [
    "Springfield",
    "Riverside",
    "Fairview",
    "Madison",
    "Georgetown",
    "Clinton",
    "Franklin",
    "Greenville",
    "Bristol",
    "Ashland",
]
REPAIR_SHOPS = [
    "Apex Auto Body",
    "Summit Collision Center",
    "Harbor Paint & Repair",
    "Valley Motors Body Shop",
    "Crown Auto Restorations",
    "Metro Collision Works",
    "Pioneer Body & Frame",
    "Lakeside Auto Care",
    "Frontier Collision",
    "Northside Paint Pros",
]


def _fail(message: str) -> None:
    print(f"SEED ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def _stable_int(key: str, mod: int) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % mod


def _derive_phone(policy: str) -> str:
    n = _stable_int(f"phone:{policy}", 9_000_000_000) + 1_000_000_000
    return f"+1-{str(n)[:3]}-{str(n)[3:6]}-{str(n)[6:10]}"


def _derive_bank(policy: str) -> str:
    n = _stable_int(f"bank:{policy}", 10**12)
    return f"****{n:012d}"[-16:]


def _derive_vin(policy: str) -> str:
    alphabet = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
    seed = _stable_int(f"vin:{policy}", 10**9)
    chars = []
    x = seed
    for _ in range(17):
        chars.append(alphabet[x % len(alphabet)])
        x = (x * 1103515245 + 12345) % (2**31)
    return "".join(chars)


def _derive_name(policy: str) -> str:
    fi = _stable_int(f"fn:{policy}", len(FIRST_NAMES))
    li = _stable_int(f"ln:{policy}", len(LAST_NAMES))
    return f"{FIRST_NAMES[fi]} {LAST_NAMES[li]}"


def _derive_address(policy: str, accident_area: str) -> str:
    street_no = _stable_int(f"st:{policy}", 9000) + 100
    city = CITIES[_stable_int(f"city:{policy}", len(CITIES))]
    area = accident_area or "Urban"
    return f"{street_no} Maple Ave, {city} ({area})"


def _derive_repair_shop(policy: str) -> str:
    return REPAIR_SHOPS[_stable_int(f"shop:{policy}", len(REPAIR_SHOPS))]


def _parse_incident_date(row: pd.Series) -> date:
    year = int(row.get("Year", 1994) or 1994)
    month = MONTH_MAP.get(str(row.get("Month", "Jan")), 1)
    week = int(row.get("WeekOfMonth", 1) or 1)
    day = min(28, max(1, (week - 1) * 7 + 1))
    return date(year, month, day)


def _parse_submitted_at(row: pd.Series, incident: date) -> datetime:
    claimed_month = MONTH_MAP.get(str(row.get("MonthClaimed", "")), incident.month)
    claimed_week = int(row.get("WeekOfMonthClaimed", 1) or 1)
    year = incident.year
    # Claims filed in Jan after Dec incident → next year
    if claimed_month < incident.month and incident.month >= 11:
        year = incident.year + 1
    day = min(28, max(1, (claimed_week - 1) * 7 + 2))
    try:
        submitted = date(year, claimed_month, day)
    except ValueError:
        submitted = incident + timedelta(days=7)
    if submitted < incident:
        submitted = incident + timedelta(days=3)
    hour = _stable_int(f"hour:{row['PolicyNumber']}", 10) + 8
    return datetime(submitted.year, submitted.month, submitted.day, hour, 0, 0)


def _claim_amount(row: pd.Series) -> float:
    band = str(row.get("VehiclePrice", "")).strip()
    base = VEHICLE_PRICE_MIDPOINTS.get(band, 30000.0)
    # Claim is typically a fraction of vehicle value; vary by deductible & rating
    deductible = float(row.get("Deductible", 400) or 400)
    rating = float(row.get("DriverRating", 1) or 1)
    fraction = (
        0.12 + (rating * 0.03) + (_stable_int(f"amt:{row['PolicyNumber']}", 40) / 100.0)
    )
    amount = max(500.0, base * fraction - deductible * 0.5)
    # Occasional round numbers (useful for rule engine later)
    if _stable_int(f"round:{row['PolicyNumber']}", 20) == 0:
        amount = round(amount / 1000.0) * 1000.0
    return round(amount, 2)


def _description(row: pd.Series) -> str:
    make = row.get("Make", "Vehicle")
    fault = row.get("Fault", "Unknown")
    area = row.get("AccidentArea", "Unknown")
    policy_type = row.get("PolicyType", "Unknown")
    return (
        f"{make} incident in {area} area. Fault: {fault}. "
        f"Policy type: {policy_type}. Past claims: {row.get('PastNumberOfClaims', 'unknown')}."
    )


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        _fail(
            f"Dataset not found at {path}.\n"
            "Download the Kaggle dataset "
            "'Vehicle Insurance Claim Fraud Detection' "
            "(https://www.kaggle.com/datasets/shivamb/vehicle-claim-fraud-detection) "
            "and place it at backend/data/raw/claims.csv"
        )

    try:
        df = pd.read_csv(path)
    except Exception as exc:  # noqa: BLE001
        _fail(f"Failed to parse CSV at {path}: {exc}")

    if df.empty:
        _fail(f"CSV at {path} is empty.")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        _fail(
            "CSV is missing required columns: "
            + ", ".join(sorted(missing))
            + f"\nFound columns: {', '.join(df.columns)}"
        )

    return df


def row_to_claim(row: pd.Series) -> Claim:
    policy = str(row["PolicyNumber"])
    incident = _parse_incident_date(row)
    submitted = _parse_submitted_at(row, incident)
    fraud_raw = row["FraudFound_P"]
    fraud_label = bool(int(fraud_raw)) if pd.notna(fraud_raw) else None

    return Claim(
        policy_number=policy,
        claimant_name=_derive_name(policy),
        claimant_phone=_derive_phone(policy),
        claimant_address=_derive_address(policy, str(row.get("AccidentArea", ""))),
        bank_account=_derive_bank(policy),
        vehicle_vin=_derive_vin(policy),
        incident_date=incident,
        claim_type=str(row.get("BasePolicy", "Unknown")),
        claim_amount=_claim_amount(row),
        description=_description(row),
        repair_shop=_derive_repair_shop(policy),
        submitted_at=submitted,
        fraud_score=None,
        fraud_label=fraud_label,
        status="open",
        age=int(row["Age"]) if pd.notna(row.get("Age")) else None,
        vehicle_category=(
            str(row.get("VehicleCategory"))
            if pd.notna(row.get("VehicleCategory"))
            else None
        ),
        vehicle_price_band=(
            str(row.get("VehiclePrice")) if pd.notna(row.get("VehiclePrice")) else None
        ),
        accident_area=(
            str(row.get("AccidentArea")) if pd.notna(row.get("AccidentArea")) else None
        ),
        fault=str(row.get("Fault")) if pd.notna(row.get("Fault")) else None,
        past_number_of_claims=(
            str(row.get("PastNumberOfClaims"))
            if pd.notna(row.get("PastNumberOfClaims"))
            else None
        ),
        age_of_vehicle=(
            str(row.get("AgeOfVehicle")) if pd.notna(row.get("AgeOfVehicle")) else None
        ),
        police_report_filed=(
            str(row.get("PoliceReportFiled"))
            if pd.notna(row.get("PoliceReportFiled"))
            else None
        ),
        witness_present=(
            str(row.get("WitnessPresent"))
            if pd.notna(row.get("WitnessPresent"))
            else None
        ),
        base_policy=(
            str(row.get("BasePolicy")) if pd.notna(row.get("BasePolicy")) else None
        ),
        days_policy_claim=(
            str(row.get("Days_Policy_Claim"))
            if pd.notna(row.get("Days_Policy_Claim"))
            else None
        ),
        address_change_claim=(
            str(row.get("AddressChange_Claim"))
            if pd.notna(row.get("AddressChange_Claim"))
            else None
        ),
        deductible=int(row["Deductible"]) if pd.notna(row.get("Deductible")) else None,
        driver_rating=(
            int(row["DriverRating"]) if pd.notna(row.get("DriverRating")) else None
        ),
        sex=str(row.get("Sex")) if pd.notna(row.get("Sex")) else None,
        make=str(row.get("Make")) if pd.notna(row.get("Make")) else None,
    )


def simple_row_to_claim(row: pd.Series) -> Claim:
    """Parse a simple (analyst) CSV row into a Claim model instance."""
    incident_raw = row["incident_date"]
    if isinstance(incident_raw, datetime):
        incident = incident_raw.date()
    elif isinstance(incident_raw, date):
        incident = incident_raw
    else:
        incident = date.fromisoformat(str(incident_raw).strip()[:10])

    submitted_raw = row.get("submitted_at")
    if (
        pd.isna(submitted_raw)
        or submitted_raw is None
        or str(submitted_raw).strip() == ""
    ):
        submitted = datetime.combine(incident, datetime.min.time()).replace(hour=10)
    elif isinstance(submitted_raw, datetime):
        submitted = submitted_raw
    else:
        submitted = datetime.fromisoformat(str(submitted_raw).strip().replace("Z", ""))

    def _opt_str(key: str) -> str | None:
        val = row.get(key)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        text = str(val).strip()
        return text or None

    def _opt_int(key: str) -> int | None:
        val = row.get(key)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    return Claim(
        policy_number=str(row["policy_number"]).strip(),
        claimant_name=str(row["claimant_name"]).strip(),
        claimant_phone=str(row["claimant_phone"]).strip(),
        claimant_address=str(row["claimant_address"]).strip(),
        bank_account=str(row["bank_account"]).strip(),
        vehicle_vin=str(row["vehicle_vin"]).strip(),
        incident_date=incident,
        claim_type=str(row["claim_type"]).strip(),
        claim_amount=float(row["claim_amount"]),
        description=str(row.get("description") or "").strip(),
        repair_shop=str(row["repair_shop"]).strip(),
        submitted_at=submitted,
        fraud_score=None,
        fraud_label=None,
        status="pending",
        age=_opt_int("age"),
        vehicle_category=_opt_str("vehicle_category"),
        vehicle_price_band=_opt_str("vehicle_price_band"),
        accident_area=_opt_str("accident_area"),
        fault=_opt_str("fault"),
        past_number_of_claims=_opt_str("past_number_of_claims"),
        age_of_vehicle=_opt_str("age_of_vehicle"),
        police_report_filed=_opt_str("police_report_filed"),
        witness_present=_opt_str("witness_present"),
        base_policy=_opt_str("base_policy") or str(row["claim_type"]).strip(),
        days_policy_claim=_opt_str("days_policy_claim"),
        address_change_claim=_opt_str("address_change_claim"),
        deductible=_opt_int("deductible"),
        driver_rating=_opt_int("driver_rating"),
        sex=_opt_str("sex"),
        make=_opt_str("make"),
    )


def seed_demo_if_empty() -> int:
    """
    If the claims table is empty, load the small committed demo CSV and inject
    fraud-ring rows. Safe for Render free-tier cold starts / redeploys.
    Returns the number of claims after seeding (0 if DB already had data).
    """
    init_db()
    db = SessionLocal()
    try:
        existing = db.scalar(select(func.count()).select_from(Claim)) or 0
        if existing > 0:
            return 0

        if not DEMO_CSV.is_file():
            print(
                f"DEMO SEED: {DEMO_CSV} missing; injecting fraud rings only.",
                file=sys.stderr,
            )
            ring_count = inject_demo_fraud_rings(db)
            db.commit()
            total = db.scalar(select(func.count()).select_from(Claim)) or 0
            print(f"Auto-seeded {total} demo claims ({ring_count} fraud-ring rows).")
            return int(total)

        df = pd.read_csv(DEMO_CSV, comment="#")
        if df.empty:
            print("DEMO SEED: claims_demo.csv has no rows.", file=sys.stderr)
            return 0

        df.columns = [str(c).strip().lower() for c in df.columns]
        missing = SIMPLE_REQUIRED - set(df.columns)
        if missing:
            print(
                "DEMO SEED: claims_demo.csv missing columns: "
                + ", ".join(sorted(missing)),
                file=sys.stderr,
            )
            return 0

        batch: list[Claim] = []
        for _, row in df.iterrows():
            batch.append(simple_row_to_claim(row))
        db.add_all(batch)
        db.commit()

        ring_count = inject_demo_fraud_rings(db)
        db.commit()

        total = int(db.scalar(select(func.count()).select_from(Claim)) or 0)
        print(
            f"Auto-seeded {total} demo claims "
            f"({len(batch)} from CSV, {ring_count} fraud-ring rows)."
        )
        return total
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"DEMO SEED failed (continuing with empty DB): {exc}", file=sys.stderr)
        return 0
    finally:
        db.close()


def inject_demo_fraud_rings(db) -> int:
    """
    demo seed data for fraud ring visualization

    The source dataset has no shared phone/bank/VIN entities across claims.
    Inject a small handful of synthetic linked claims so the network graph
    demo has connected components of size >= 3.
    """
    rings = [
        {
            "tag": "RING-ALPHA",
            "phone": "+1-555-010-1001",
            "bank": "****111122223333",
            "address": "100 Fraud Ring Lane, Springfield (Urban)",
            "shop": "Shadow Collision Collective",
            "count": 4,
        },
        {
            "tag": "RING-BETA",
            "phone": "+1-555-010-2002",
            "bank": "****444455556666",
            "vin": "RINGBETA000000001",
            "address": "200 Syndicate Blvd, Riverside (Urban)",
            "shop": "Syndicate Auto Body",
            "count": 3,
        },
    ]

    added = 0
    for ring in rings:
        for i in range(ring["count"]):
            policy = f"{ring['tag']}-{i + 1:02d}"
            claim = Claim(
                policy_number=policy,
                claimant_name=f"Demo Claimant {ring['tag']}-{i + 1}",
                claimant_phone=ring["phone"] if i < 3 else _derive_phone(policy),
                claimant_address=ring["address"],
                bank_account=ring["bank"] if i != 1 else _derive_bank(policy),
                vehicle_vin=(
                    ring.get("vin", _derive_vin(policy))
                    if i < 2
                    else _derive_vin(policy)
                ),
                incident_date=date(2023, 6, 10 + i),
                claim_type="Collision",
                claim_amount=12000.0 + i * 500,
                description=f"Demo linked claim for fraud ring visualization ({ring['tag']}).",
                repair_shop=ring["shop"],
                submitted_at=datetime(2023, 6, 12 + i, 10, 0, 0),
                fraud_score=None,
                fraud_label=True,
                status="flagged",
                age=35 + i,
                vehicle_category="Sedan",
                vehicle_price_band="30000 to 39000",
                accident_area="Urban",
                fault="Policy Holder",
                past_number_of_claims="2 to 4",
                age_of_vehicle="5 years",
                police_report_filed="No",
                witness_present="No",
                base_policy="Collision",
                days_policy_claim="none",
                address_change_claim="under 6 months",
                deductible=400,
                driver_rating=1,
                sex="Male",
                make="Honda",
            )
            db.add(claim)
            added += 1
    return added


def seed(limit: int | None = None) -> None:
    df = load_csv(RAW_CSV)
    if limit is not None:
        df = df.head(limit)

    init_db()

    # Reset claims table for idempotent seeding
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM claims"))

    db = SessionLocal()
    try:
        batch: list[Claim] = []
        for _, row in df.iterrows():
            batch.append(row_to_claim(row))
            if len(batch) >= 500:
                db.add_all(batch)
                db.commit()
                batch = []
        if batch:
            db.add_all(batch)
            db.commit()

        demo_count = inject_demo_fraud_rings(db)
        db.commit()

        total = db.scalar(select(func.count()).select_from(Claim)) or 0
        sample = db.scalars(select(Claim).limit(1)).first()

        print(f"Seeded {total} claims ({demo_count} demo fraud-ring rows).")
        if sample:
            print(
                "Sample row:",
                {
                    "id": sample.id,
                    "policy_number": sample.policy_number,
                    "claimant_name": sample.claimant_name,
                    "claim_type": sample.claim_type,
                    "claim_amount": sample.claim_amount,
                    "fraud_label": sample.fraud_label,
                    "status": sample.status,
                    "incident_date": str(sample.incident_date),
                },
            )
    finally:
        db.close()


if __name__ == "__main__":
    seed_limit = None
    if len(sys.argv) > 1:
        seed_limit = int(sys.argv[1])
    seed(limit=seed_limit)
