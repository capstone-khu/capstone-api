# capstone-api

## 로컬 실행

```bash
# 1) MySQL 컨테이너 실행 (localhost:3306)
docker compose up -d db

# 2) 의존성 설치 (가상환경 자동 생성)
uv sync

# 3) 환경변수 설정
cp .env.example .env   # 값 수정

# 4) 개발 서버 실행
uv run fastapi dev app/main.py
```

- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health
