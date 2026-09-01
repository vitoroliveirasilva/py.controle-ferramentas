from __future__ import annotations

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by all SQLAlchemy models"""


db = SQLAlchemy(model_class=Base, session_options={"expire_on_commit": False})
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
