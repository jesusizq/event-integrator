from apifairy import APIFairy
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_cors import CORS
from celery import Celery

import os
import tempfile

db = SQLAlchemy()
migrate = Migrate()
apifairy = APIFairy()
cors = CORS()
ma = Marshmallow()
celery = Celery()
cache = Cache(  # Keep this initialization with config
    config={
        "CACHE_TYPE": "FileSystemCache",
        "CACHE_DIR": os.path.join(tempfile.gettempdir(), "cache"),
        "CACHE_DEFAULT_TIMEOUT": 300,  # 5 minutes
    }
)
