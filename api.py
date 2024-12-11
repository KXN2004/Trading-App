from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, RedirectResponse, HTMLResponse
from starlette import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from upstox_client import LoginApi
from upstox_client.rest import ApiException

from models import Credentials
from config import DATABASE, LOGIN_URL as login_endpoint, REDIRECT_URL as redirect_url
from urllib.parse import urlencode

app = FastAPI()


@app.get("/")
def read_root():
    return PlainTextResponse(
        status_code=status.HTTP_200_OK,
        content="Connected to Upstox Auth Service!"
    )


@app.get("/login/{client_id}")
def login(client_id: str):
    engine = create_engine(f"sqlite:///{DATABASE}")
    Session = sessionmaker(bind=engine)
    with Session() as database:
        if client_id.islower():
            client_id = client_id.upper()
        client = database.query(Credentials).get(client_id)
        if client is None:
            return PlainTextResponse(
                status_code=status.HTTP_404_NOT_FOUND, content="User not found"
            )
        query_params = {
            "client_id": client.api_key,
            "redirect_uri": redirect_url,
            "state": client.client_id,  # The state is the client_id itself!
            "response_type": "code",
        }
        return RedirectResponse(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            url=f"{login_endpoint}?{urlencode(query_params)}",
        )


@app.get("/callback")
def callback(code: str, state: str):
    engine = create_engine(f"sqlite:///{DATABASE}")
    Session = sessionmaker(bind=engine)
    with Session() as database:
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
        html_content = file.read()
    return HTMLResponse(status_code=status.HTTP_200_OK, content=html_content)
