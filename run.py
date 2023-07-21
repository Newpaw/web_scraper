import uvicorn
import httpx
import secrets

from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Path
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.params import Depends
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import Column, String, create_engine

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from scraper import scrape_website_async
from logging_conf import logger

SQLALCHEMY_DATABASE_URL = "sqlite:///./sqlite.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    client_id = Column(String, primary_key=True, index=True)
    webhook_url = Column(String)


Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def root():
    response = RedirectResponse(url='/docs')
    return response

@app.post("/register", response_model=None)
async def register(db: Session = Depends(get_db)):
    new_client_id = secrets.token_urlsafe(16)
    db.add(User(client_id=new_client_id))
    db.commit()
    return {"client_id": new_client_id}


@app.post("/webhook/{client_id}", response_model=None)
async def register_webhook(
    client_id: str, webhook_url: str, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.client_id == client_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid client id")
    user.webhook_url = webhook_url
    db.commit()
    return {"message": "Webhook registered successfully"}


@app.get("/scrape/{base_url:path}", response_model=None)
async def scrape(
    base_url: str, client_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.client_id == client_id).first()
    logger.warning(f"Sarted scraping {base_url}")
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid client id")

    # Add the scraping task to the background tasks queue
    background_tasks.add_task(scrape_and_notify, db, client_id, base_url)

    return JSONResponse(status_code=202, content={"message": "Scrape job started"})



async def scrape_and_notify(db: Session, client_id: str, base_url: str):
    records = await scrape_website_async(f"https://{base_url}/")
    logger.warning(f"Finished scraping {base_url}")
    await notify_webhook(db, client_id, {"records": [record.__dict__ for record in records]})


async def notify_webhook(db: Session, client_id: str, data: dict):
    """Sends data to the registered webhook"""
    user = db.query(User).filter(User.client_id == client_id).first()
    if user and user.webhook_url:
        async with httpx.AsyncClient() as client:
            await client.post(user.webhook_url, json=data)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
