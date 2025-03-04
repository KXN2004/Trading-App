from urllib.parse import urlencode

from config import TEMPLATES, get_settings
from database import Session, engine
from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    Response,
)
from models import Credentials
from upstox_client import LoginApi
from upstox_client.rest import ApiException

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
)


def get_session():
    with Session(engine) as session:
        yield session


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
    except ApiException as e:
        print("Exception when calling LoginApi->token: %s\n" % e)
    client.access_token = login_info.access_token
    database.commit()
    with open(f"{TEMPLATES}/close_tab.html", "r") as file:
        close_tab_html = file.read()
    return HTMLResponse(close_tab_html)
