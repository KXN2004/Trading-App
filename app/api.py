from urllib.parse import urlencode

from fastapi import Depends, FastAPI
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    Response,
)
from upstox_client import LoginApi
from upstox_client.rest import ApiException

from config import LOGIN_URL as login_endpoint
from config import REDIRECT_URL as redirect_url
from database import Session
from models import Credentials

app = FastAPI()


def get_session():
    with Session() as session:
        yield session


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return FileResponse("favicon.ico")


@app.get("/login/{client_id}")
def login(client_id: str, database=Depends(get_session)) -> Response:
    client_id = client_id if client_id.isupper() else client_id.upper()
    client = database.query(Credentials).get(client_id)
    if client is None:
        with open("unknown_user.html", "r") as f:
            unknown_user_html = f.read()
        return HTMLResponse(unknown_user_html)
    query_params = {
        "client_id": client.api_key,
        "redirect_uri": redirect_url,
        "state": client.client_id,  # The state is the client id itself!
        "response_type": "code",
    }
    return RedirectResponse(f"{login_endpoint}?{urlencode(query_params)}")


@app.get("/callback")
def callback(code: str, state: str, database=Depends(get_session)) -> Response:
    # The state variable is the client_id
    client = database.query(Credentials).get(state)
    try:
        login_info = LoginApi().token(
            api_version="2.0",
            code=code,
            client_id=client.api_key,
            client_secret=client.api_secret,
            redirect_uri=redirect_url,
            grant_type="authorization_code",
        )
    except ApiException as e:
        print("Exception when calling LoginApi->token: %s\n" % e)
    client.access_token = login_info.access_token
    database.commit()
    with open("close_tab.html", "r") as file:
        close_tab_html = file.read()
    return HTMLResponse(close_tab_html)
