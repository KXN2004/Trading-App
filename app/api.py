from contextlib import asynccontextmanager
from urllib.parse import urlencode

from config import TEMPLATES, get_settings
from database import Session, engine
from database import get_session as database_session
from fastapi import Depends, FastAPI, status
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    Response,
)
from models import Credentials
from sqlmodel import update
from upstox_client import LoginApi
from upstox_client.rest import ApiException


def get_session():
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Reset the is_active attribute to 0 whenever the server starts
    database: Session = database_session()
    database.exec(update(Credentials).values(is_active=0))
    database.commit()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return FileResponse("favicon.ico")


@app.get("/login/{client_id}")
def login(client_id: str, database=Depends(get_session)) -> Response:
    client_id = client_id if client_id.isupper() else client_id.upper()
    client = database.query(Credentials).get(client_id)
    settings = get_settings()
    if client is None:
        with open(f"{TEMPLATES}/unknown_user.html", "r") as f:
            unknown_user_html = f.read()
        return HTMLResponse(
            status_code=status.HTTP_404_NOT_FOUND, content=unknown_user_html
        )
    query_params = {
        "client_id": client.api_key,
        "redirect_uri": settings.redirect_uri,
        "state": client.client_id,  # The state is the client id itself!
        "response_type": "code",
    }
    return RedirectResponse(f"{settings.login_url}?{urlencode(query_params)}")


@app.get("/callback")
def callback(code: str, state: str, database=Depends(get_session)) -> Response:
    # The state variable is the client_id
    client = database.query(Credentials).get(state)
    settings = get_settings()
    try:
        login_info = LoginApi().token(
            api_version="2.0",
            code=code,
            client_id=client.api_key,
            client_secret=client.api_secret,
            redirect_uri=settings.redirect_uri,
            grant_type="authorization_code",
        )
        client.is_active = 1
        client.access_token = login_info.access_token
        database.commit()
        with open(f"{TEMPLATES}/close_tab.html", "r") as close_tab_html:
            return HTMLResponse(close_tab_html.read())
    except ApiException as e:
        print("Exception when calling LoginApi->token: %s\n" % e)
        with open(f"{TEMPLATES}/internal_error.html", "r") as internal_error_html:
            return HTMLResponse(internal_error_html.read())
