# Base image: Python 3.13 (yoki sizga kerakli versiya)
FROM python:3.13-slim

# Ishchi papkani yaratamiz va unga o‘tamiz
WORKDIR /app

# requirements.txt ni containerga nusxalash
COPY requirements.txt .

# Dependencies o‘rnatamiz
RUN pip install --no-cache-dir -r requirements.txt

# Ilova fayllarini nusxalash
COPY . .

# FastAPI serverni uvicorn orqali ishga tushiramiz
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
