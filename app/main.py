# app/main.py
from fastapi import FastAPI
from app.routers.fetch import router as fetch_router

app = FastAPI(title="Shopify Insights Fetcher (MVP)")

app.include_router(fetch_router, prefix="")

# root health
@app.get("/")
async def root():
    return {"ok": True, "message": "Shopify Insights Fetcher API"}

# If running directly (for convenience)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
