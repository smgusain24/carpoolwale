import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

from application.users.views import router as users_router
from application.ride.views import router as rides_router

app.include_router(users_router)
app.include_router(rides_router)

@app.get("/health")
def health():
    return JSONResponse(content={'msg': 'Server is running fine'}, status_code=200)


if __name__ == "__main__":
    uvicorn.run(app)