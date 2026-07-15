from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.auth import user_login

app = FastAPI()