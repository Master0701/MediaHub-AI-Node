from app.database import Base, engine
import app.models

Base.metadata.create_all(bind=engine)

print("MediaHub-Datenbank erstellt.")
