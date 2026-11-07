from fastapi import FastAPI

app = FastAPI(title="Carousel Prep API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
