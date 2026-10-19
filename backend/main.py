"""Run from the project root: python -m uvicorn backend.main:app --reload."""
import logging
import os

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import schemas, services

API_VERSION = "1.0.0"
app = FastAPI(title="SmartEnergyAI API", version=API_VERSION,
              description="Single-observation Appliances forecasting in Wh, 10 minutes ahead. Requires 42 already-engineered features. Recommendations are decision support only; no automatic control or guaranteed savings.")
origins = os.environ.get("SMARTENERGY_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8080")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in origins.split(",") if o.strip() and o.strip() != "*"],
                   allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.exception_handler(RequestValidationError)
async def request_error(request: Request, exc: RequestValidationError):
    # Do not echo raw invalid input: JSON NaN/Infinity cannot be serialized safely.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()
    ]})


@app.exception_handler(services.InvalidFeatures)
async def feature_error(request: Request, exc: services.InvalidFeatures):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(services.ResourceUnavailable)
async def resource_error(request: Request, exc: services.ResourceUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logging.getLogger(__name__).error("API operation failed", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Unable to complete the operation."})


@app.get("/", response_model=schemas.RootResponse)
def root():
    return {"name": app.title, "version": app.version, "docs": "/docs"}


@app.get("/health", response_model=schemas.HealthResponse, responses={503: {"model": schemas.HealthResponse}},
         description="Load/verify cached model and threshold resources without predicting. Missing resources return 503; successful resources are reused until process restart.")
def health(response: Response):
    result = services.health()
    if result["status"] != "ok":
        response.status_code = 503
    return result


@app.get("/model/info", response_model=schemas.ModelInfoResponse,
         description="Safe metadata and the existing Phase 11 held-out performance estimate; no new evaluation.")
def model_info():
    return services.model_info()


@app.post("/forecast", response_model=schemas.ForecastResponse,
          description="Predict one already-engineered observation using the persisted model. No raw feature engineering, clipping or uncertainty estimation.")
def forecast(body: schemas.ForecastRequest):
    return services.forecast(body.features)


@app.post("/forecast/recommendation", response_model=schemas.RecommendationResponse,
          description="Use the unchanged Phase 14 integrated helper and development-calibrated thresholds. No automatic equipment control or savings estimates.")
def forecast_recommendation(body: schemas.ForecastRequest):
    return services.forecast_recommendation(body.features)


@app.get("/recommendations/thresholds", response_model=schemas.ThresholdResponse,
         description="Existing TRAIN + VALIDATION percentile thresholds in Wh and inclusive/exclusive band definitions. No recalibration.")
def recommendation_thresholds():
    return services.threshold_info()
