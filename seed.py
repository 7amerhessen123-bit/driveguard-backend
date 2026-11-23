from database import SessionLocal
from models import Company, User
from security import hash_password

db = SessionLocal()

company = db.query(Company).filter(Company.name == "Nile Fleet").first()
if not company:
    company = Company(name="Nile Fleet")
    db.add(company)
    db.commit()
    db.refresh(company)

accounts = [
    {"name": "Mona Adel", "email": "admin@driveguard.test",
     "role": "ADMIN", "shift": None, "active": True},
    {"name": "Omar Khaled", "email": "driver.ready@driveguard.test",
     "role": "DRIVER", "shift": "MORNING", "active": True},
    {"name": "Disabled Driver", "email": "driver.off@driveguard.test",
     "role": "DRIVER", "shift": "MORNING", "active": False},
]

for a in accounts:
    exists = db.query(User).filter(User.email == a["email"]).first()
    if exists:
        continue
    db.add(User(
        company_id=company.id,
        name=a["name"],
        email=a["email"],
        password_hash=hash_password("Test@1234"),
        role=a["role"],
        shift=a["shift"],
        is_active=a["active"],
        consent_given=True,
        has_face_profile=True,
    ))

db.commit()
db.close()
print("seed done")