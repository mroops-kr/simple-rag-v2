from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from routers import api_v2_share, api_v2_user

# 프로잭트 경로 환경변수 잡기
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 환경변수 읽기
from dotenv import load_dotenv
load_dotenv()

# app 선언
app = FastAPI()

# 라우터 include
routers = [api_v2_share, api_v2_user]
for router in routers:
    app.include_router(router.router, prefix=router.prefix)

# 루트경로
@app.get("/")
async def root():
    return RedirectResponse(url='/docs', status_code=302)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

#       uvicorn main:app --reload