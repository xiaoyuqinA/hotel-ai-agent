FROM python:3.13-slim

WORKDIR /app

# 安装系统依赖（如需要 psycopg2 编译）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制项目依赖文件
COPY pyproject.toml .

# 安装 Python 依赖
RUN pip install --no-cache-dir -e ".[event-store]"

# 复制项目代码
COPY . .

# 创建 storage 目录
RUN mkdir -p storage

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
