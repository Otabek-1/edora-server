from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import asyncpg
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
import os

SECRET_KEY = os.getenv("SECRET_KEY", "secret123")
ALGORITHM = "HS256"
EXPIRE_MINUTES = 30

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# PostgreSQL connection pool
async def get_db():
    pool = await asyncpg.create_pool(
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        database=os.getenv("PGDATABASE"),
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT", 5432)
    )
    async with pool.acquire() as conn:
        yield conn
    await pool.close()

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

@app.middleware("https")
async def auth_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "DELETE"):
        public_paths = ["/login"]
        if request.url.path not in public_paths:
            token = request.headers.get("Authorization")
            if not token:
                return JSONResponse(status_code=401, content={"detail": "Token kerak"})
            try:
                scheme, _, token_value = token.partition(" ")
                if scheme.lower() != "bearer":
                    raise JWTError("Bearer bo'lishi kerak")
                jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
            except JWTError:
                return JSONResponse(status_code=401, content={"detail": "Yaroqsiz token"})
    response = await call_next(request)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://edora.netlify.app", "https://edora-ashy.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def greeting(db: asyncpg.Connection = Depends(get_db)):
    async with db.transaction():
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
    async with db.transaction():
        result = await db.fetch("SELECT * FROM subject")
    return {"data": [dict(record) for record in result]}

@app.post("/subject")
async def add_subject(data: Subject, db: asyncpg.Connection = Depends(get_db)):
    async with db.transaction():
        try:
            await db.execute("INSERT INTO subject(name, tags) VALUES ($1, $2)", data.name, data.tags)
            return {"message": "Muvaffaqiyatli qo'shildi!"}
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail={"message": "Error in add_subject. See logs"})

@app.put("/subject/{id}")
async def update_subject(id: int, data: Subject, db: asyncpg.Connection = Depends(get_db)):
    async with db.transaction():
        try:
            result = await db.fetchrow("SELECT * FROM subject WHERE id = $1", id)
            if not result:
                raise HTTPException(status_code=404, detail={"message": "Subject mavjud emas."})
            await db.execute("UPDATE subject SET name = $1, tags = $2 WHERE id = $3", data.name, data.tags, id)
            return {"message": "Muvaffaqiyatli o'zgartirildi!"}
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail={"message": "Error in update_subject. See logs"})

@app.delete("/subject/{id}")
async def delete_subject(id: int, db: asyncpg.Connection = Depends(get_db)):
    async with db.transaction():
        try:
            result = await db.fetchrow("SELECT * FROM subject WHERE id = $1", id)
            if not result:
                raise HTTPException(status_code=404, detail={"message": "Subject mavjud emas."})
            await db.execute("DELETE FROM subject WHERE id = $1", id)
            return {"message": "Muvaffaqiyatli o'chirildi!"}
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail={"message": "Error in delete_subject. See logs"})

@app.get("/themes")
async def get_themes(db: asyncpg.Connection = Depends(get_db)):
    async with db.transaction():
        result = await db.fetch("SELECT * FROM theme")
    return {"data": [dict(record) for record in result]}

@app.post("/theme")
async def add_theme(data: Theme, db: asyncpg.Connection = Depends(get_db)):
    async with db.transaction():
        try:
            subject_exists = await db.fetchrow("SELECT id FROM subject WHERE id = $1", data.subject_id)
            if not subject_exists:
                raise HTTPException(status_code=404, detail={"message": "Bunday subject mavjud emas."})
            await db.execute(
                "INSERT INTO theme(subject_id, title, content, tags) VALUES ($1, $2, $3, $4)",
                data.subject_id, data.title, data.content, data.tags
            )
            return {"message": "Theme muvaffaqiyatli qo'shildi!"}
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail={"message": "Error in add_theme. See logs"})

@app.put("/theme/{id}")
async def update_theme(id: int, data: Theme, db: asyncpg.Connection = Depends(get_db)):
    async with db.transaction():
        try:
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
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail={"message": "Error in update_theme. See logs"})

@app.delete("/theme/{id}")
async def delete_theme(id: int, db: asyncpg.Connection = Depends(get_db)):
    async with db.transaction():
        try:
            theme_exists = await db.fetchrow("SELECT id FROM theme WHERE id = $1", id)
            if not theme_exists:
                raise HTTPException(status_code=404, detail={"message": "Theme mavjud emas."})
            await db.execute("DELETE FROM theme WHERE id = $1", id)
            return {"message": "Theme muvaffaqiyatli o'chirildi!"}
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail={"message": "Error in delete_theme. See logs"})
