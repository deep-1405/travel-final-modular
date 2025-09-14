from fastapi import FastAPI
from backend.routers.geolocation import router as geolocation_router
from backend.routers.airports import router as airports_router
from backend.routers.flights import router as flights_router

app = FastAPI()
app.include_router(geolocation_router)
app.include_router(airports_router)
app.include_router(flights_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)