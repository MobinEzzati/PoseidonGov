from fastapi import FastAPI

from app.routers import companies, fleet, health, memo

app = FastAPI(title="PoseidonGov API")

app.include_router(health.router)
app.include_router(companies.router)
app.include_router(fleet.router)
app.include_router(memo.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
