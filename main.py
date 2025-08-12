from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import sqlite3
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware

SECRET_KEY = "secret123"
ALGORITHM = "HS256"
EXPIRE_MINUTES = 30

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_hashed_password(password:str):
    return pwd_context.hash(password)

def verify_password(plain:str, hashed:str):
    return pwd_context.verify(plain, hashed)

def create_token(data:dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow()+ (expires_delta or timedelta(minutes=EXPIRE_MINUTES))
    to_encode.update({"exp":expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


conn = sqlite3.connect("Edora.db" ,check_same_thread=False)
conn.execute("PRAGMA foreign_keys = ON")

class Token(BaseModel):
    access_token:str
    token_type:str
    
class Subject(BaseModel):
    name:str
    tags:str

class Theme(BaseModel):
    subject_id:int
    title:str
    content:str
    tags:str

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Faqat POST, PUT, DELETE uchun JWT tekshiriladi
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
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def greeting():
    cursor = conn.cursor()
    res = cursor.execute("PRAGMA user_version").fetchone()
    return {"user_version": res[0]}

@app.post("/login", response_model=Token)
def login(form_data:OAuth2PasswordRequestForm = Depends()):
    login = "admin"
    password = get_hashed_password("1234")
    try:
        if not verify_password(form_data.password, password) or login != form_data.username:
            raise HTTPException(status_code=400, detail={"message":"Parol yoki username xato!"})
        token = create_token(data={"sub":form_data.username})
        return {"access_token":token, "token_type":"bearer"}
    finally:
        pass

@app.get("/subjects")
def get_subjects():
    cursor = conn.cursor()
    result = cursor.execute("SELECT * FROM subject").fetchall()
    cursor.close()
    return {"data": result}

@app.post("/subject")
def add_subject(data:Subject):
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO subject(name, tags) VALUES (?,?)",[data.name, data.tags])
        return {"message":"Muvaffaqiyatli qo'shildi!"}
    except sqlite3.Error as e:
        print(e)
        raise HTTPException(status_code=500, detail={"message":"Error in add_subject. See logs"})
    finally:
        conn.commit()
        cursor.close()

@app.put("/subject/{id}")
def update_subject(data:Subject, id:int):
    cursor = conn.cursor()
    try:
        result = cursor.execute("SELECT * FROM subject WHERE id = ?",(id,)).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail={"message":"Subject mavjud emas."})
        cursor.execute("UPDATE subject SET name = ?, tags = ? WHERE id = ?",(data.name, data.tags, id))
        return {"message":"Muvaffaqiyatli o'zgartirildi!"}
    except sqlite3.Error as e:
        print(e)
        raise HTTPException(status_code=500, detail={"message":"Error in update_subject. See logs"})
    finally:
        conn.commit()
        cursor.close()

@app.delete("/subject/{id}")
def delete_subject(id:int):
    cursor = conn.cursor()
    try:
        result = cursor.execute("SELECT * FROM subject WHERE id = ?",(id,)).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail={"message":"Subject mavjud emas."})
        cursor.execute("DELETE FROM subject WHERE id = ?",(id,))
        return {"message":"Muvaffaqiyatli o'chirildi!"}
    except sqlite3.Error as e:
        print(e)
        raise HTTPException(status_code=500, detail={"message":"Error in delete_subject. See logs"})
    finally:
        conn.commit()
        cursor.close()

@app.get("/themes")
def get_themes():
    cursor = conn.cursor()
    result = cursor.execute("SELECT * FROM theme").fetchall()
    cursor.close()
    return {"data": result}

@app.post("/theme")
def add_theme(data: Theme):
    cursor = conn.cursor()
    try:
        subject_exists = cursor.execute("SELECT id FROM subject WHERE id = ?", (data.subject_id,)).fetchone()
        if not subject_exists:
            raise HTTPException(status_code=404, detail={"message": "Bunday subject mavjud emas."})
        cursor.execute(
            "INSERT INTO theme(subject_id, title, content, tags) VALUES (?, ?, ?, ?)",
            (data.subject_id, data.title, data.content, data.tags)
        )
        return {"message": "Theme muvaffaqiyatli qo'shildi!"}
    except sqlite3.Error as e:
        print(e)
        raise HTTPException(status_code=500, detail={"message": "Error in add_theme. See logs"})
    finally:
        conn.commit()
        cursor.close()

@app.put("/theme/{id}")
def update_theme(id: int, data: Theme):
    cursor = conn.cursor()
    try:
        theme_exists = cursor.execute("SELECT id FROM theme WHERE id = ?", (id,)).fetchone()
        if not theme_exists:
            raise HTTPException(status_code=404, detail={"message": "Theme mavjud emas."})
        subject_exists = cursor.execute("SELECT id FROM subject WHERE id = ?", (data.subject_id,)).fetchone()
        if not subject_exists:
            raise HTTPException(status_code=404, detail={"message": "Bunday subject mavjud emas."})
        cursor.execute(
            "UPDATE theme SET subject_id = ?, title = ?, content = ?, tags = ? WHERE id = ?",
            (data.subject_id, data.title, data.content, data.tags, id)
        )
        return {"message": "Theme muvaffaqiyatli o'zgartirildi!"}
    except sqlite3.Error as e:
        print(e)
        raise HTTPException(status_code=500, detail={"message": "Error in update_theme. See logs"})
    finally:
        conn.commit()
        cursor.close()

@app.delete("/theme/{id}")
def delete_theme(id: int):
    cursor = conn.cursor()
    try:
        theme_exists = cursor.execute("SELECT id FROM theme WHERE id = ?", (id,)).fetchone()
        if not theme_exists:
            raise HTTPException(status_code=404, detail={"message": "Theme mavjud emas."})
        cursor.execute("DELETE FROM theme WHERE id = ?", (id,))
        return {"message": "Theme muvaffaqiyatli o'chirildi!"}
    except sqlite3.Error as e:
        print(e)
        raise HTTPException(status_code=500, detail={"message": "Error in delete_theme. See logs"})
    finally:
        conn.commit()
        cursor.close()