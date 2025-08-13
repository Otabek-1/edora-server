import ssl
import asyncpg
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

SECRET_KEY = "secret123"
ALGORITHM = "HS256"
EXPIRE_MINUTES = 30

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

db_pool: asyncpg.Pool = None  # global pool

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Supabase ma'lumotlari ===
SUPABASE_HOST = "aws-0-eu-north-1.pooler.supabase.com"
SUPABASE_DB = "postgres"
SUPABASE_USER = "postgres.ybzmdlwxczqzvvtamjga"
SUPABASE_PASSWORD = "Ibr0him$!"
SUPABASE_PORT = 5432

async def get_db():
    async with db_pool.acquire() as conn:
        yield conn

def get_hashed_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

def create_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

class Token(BaseModel):
    access_token: str
    token_type: str

class Subject(BaseModel):
    name: str
    tags: str

class Theme(BaseModel):
    subject_id: int
    title: str
    content: str
    tags: str

@app.on_event("startup")
async def startup():
    global db_pool
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE  # sertifikatni tekshirmaydi
    dsn = f"postgresql://{SUPABASE_USER}:{SUPABASE_PASSWORD}@{SUPABASE_HOST}:{SUPABASE_PORT}/{SUPABASE_DB}"
    db_pool = await asyncpg.create_pool(dsn=dsn, ssl=ssl_context)

    async with db_pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS subject (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            tags TEXT
        );
        """)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS theme (
            id SERIAL PRIMARY KEY,
            subject_id INT NOT NULL REFERENCES subject(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            content TEXT,
            tags TEXT
        );
        """)

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close()

@app.get("/")
async def greeting(db: asyncpg.Connection = Depends(get_db)):
    res = await db.fetchval("SELECT version();")
    return {"db_version": res}

@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    login = "admin"
    password = get_hashed_password("1234")
    if not verify_password(form_data.password, password) or login != form_data.username:
        raise HTTPException(status_code=400, detail={"message": "Parol yoki username xato!"})
    token = create_token(data={"sub": form_data.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/subjects")
async def get_subjects(db: asyncpg.Connection = Depends(get_db)):
    result = await db.fetch("SELECT * FROM subject")
    return {"data": [dict(record) for record in result]}

@app.post("/subject")
async def add_subject(data: Subject, db: asyncpg.Connection = Depends(get_db)):
    await db.execute("INSERT INTO subject(name, tags) VALUES ($1, $2)", data.name, data.tags)
    return {"message": "Muvaffaqiyatli qo'shildi!"}

@app.put("/subject/{id}")
async def update_subject(id: int, data: Subject, db: asyncpg.Connection = Depends(get_db)):
    result = await db.fetchrow("SELECT * FROM subject WHERE id = $1", id)
    if not result:
        raise HTTPException(status_code=404, detail={"message": "Subject mavjud emas."})
    await db.execute("UPDATE subject SET name = $1, tags = $2 WHERE id = $3", data.name, data.tags, id)
    return {"message": "Muvaffaqiyatli o'zgartirildi!"}

@app.delete("/subject/{id}")
async def delete_subject(id: int, db: asyncpg.Connection = Depends(get_db)):
    result = await db.fetchrow("SELECT * FROM subject WHERE id = $1", id)
    if not result:
        raise HTTPException(status_code=404, detail={"message": "Subject mavjud emas."})
    await db.execute("DELETE FROM subject WHERE id = $1", id)
    return {"message": "Muvaffaqiyatli o'chirildi!"}

@app.get("/themes")
async def get_themes(db: asyncpg.Connection = Depends(get_db)):
    result = await db.fetch("SELECT * FROM theme")
    return {"data": [dict(record) for record in result]}

@app.post("/theme")
async def add_theme(data: Theme, db: asyncpg.Connection = Depends(get_db)):
    subject_exists = await db.fetchrow("SELECT id FROM subject WHERE id = $1", data.subject_id)
    if not subject_exists:
        raise HTTPException(status_code=404, detail={"message": "Bunday subject mavjud emas."})
    await db.execute(
        "INSERT INTO theme(subject_id, title, content, tags) VALUES ($1, $2, $3, $4)",
        data.subject_id, data.title, data.content, data.tags
    )
    return {"message": "Theme muvaffaqiyatli qo'shildi!"}

@app.put("/theme/{id}")
async def update_theme(id: int, data: Theme, db: asyncpg.Connection = Depends(get_db)):
    theme_exists = await db.fetchrow("SELECT id FROM theme WHERE id = $1", id)
    if not theme_exists:
        raise HTTPException(status_code=404, detail={"message": "Theme mavjud emas."})
    subject_exists = await db.fetchrow("SELECT id FROM subject WHERE id = $1", data.subject_id)
    if not subject_exists:
        raise HTTPException(status_code=404, detail={"message": "Bunday subject mavjud emas."})
    await db.execute(
        "UPDATE theme SET subject_id = $1, title = $2, content = $3, tags = $4 WHERE id = $5",
        data.subject_id, data.title, data.content, data.tags, id
    )
    return {"message": "Theme muvaffaqiyatli o'zgartirildi!"}

@app.delete("/theme/{id}")
async def delete_theme(id: int, db: asyncpg.Connection = Depends(get_db)):
    theme_exists = await db.fetchrow("SELECT id FROM theme WHERE id = $1", id)
    if not theme_exists:
        raise HTTPException(status_code=404, detail={"message": "Theme mavjud emas."})
    await db.execute("DELETE FROM theme WHERE id = $1", id)
    return {"message": "Theme muvaffaqiyatli o'chirildi!"}
