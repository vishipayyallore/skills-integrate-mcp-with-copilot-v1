from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import List, Optional
from pathlib import Path
import os


DB_FILE = Path(__file__).parent.parent / "db.sqlite3"
DATABASE_URL = f"sqlite:///{DB_FILE}"


class Participant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str
    activity_name: str


class Activity(SQLModel, table=True):
    name: str = Field(primary_key=True)
    description: Optional[str]
    schedule: Optional[str]
    max_participants: Optional[int]


engine = create_engine(DATABASE_URL, echo=False)


def init_db(seed_activities: dict | None = None):
    """Create tables and optionally seed activities if DB empty."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)

    if seed_activities:
        with Session(engine) as session:
            # Check if any activities exist
            existing = session.exec(select(Activity)).first()
            if existing:
                return

            for name, data in seed_activities.items():
                activity = Activity(
                    name=name,
                    description=data.get("description"),
                    schedule=data.get("schedule"),
                    max_participants=data.get("max_participants"),
                )
                session.add(activity)
                # add participants
                for email in data.get("participants", []):
                    p = Participant(email=email, activity_name=name)
                    session.add(p)
            session.commit()


def get_activities_from_db() -> dict:
    """Return activities as a dict matching the original API shape."""
    activities = {}
    with Session(engine) as session:
        act_list = session.exec(select(Activity)).all()
        for act in act_list:
            participants = [p.email for p in session.exec(
                select(Participant).where(Participant.activity_name == act.name)).all()]
            activities[act.name] = {
                "description": act.description,
                "schedule": act.schedule,
                "max_participants": act.max_participants,
                "participants": participants,
            }
    return activities


def add_participant(activity_name: str, email: str):
    with Session(engine) as session:
        # Check activity exists
        act = session.get(Activity, activity_name)
        if not act:
            raise KeyError("Activity not found")

        # check existing
        exists = session.exec(select(Participant).where(
            Participant.activity_name == activity_name).where(Participant.email == email)).first()
        if exists:
            raise ValueError("Already signed up")

        count = session.exec(select(Participant).where(
            Participant.activity_name == activity_name)).count()
        if act.max_participants is not None and count >= act.max_participants:
            raise RuntimeError("Activity full")

        p = Participant(email=email, activity_name=activity_name)
        session.add(p)
        session.commit()


def remove_participant(activity_name: str, email: str):
    with Session(engine) as session:
        participant = session.exec(select(Participant).where(
            Participant.activity_name == activity_name).where(Participant.email == email)).first()
        if not participant:
            raise KeyError("Not signed up")
        session.delete(participant)
        session.commit()
