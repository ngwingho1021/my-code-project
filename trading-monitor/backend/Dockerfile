FROM python:3.11-slim

WORKDIR /app

# 安裝依賴
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用
COPY backend/app.py .

# 暴露端口
EXPOSE 8000

# 啟動應用
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
