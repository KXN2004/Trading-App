from models import Credentials
from upstox_client import LoginApi
from upstox_client.rest import ApiException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import DATABASE, TRUE

schema = declarative_base().metadata

engine = create_engine(f"sqlite:///{DATABASE}")

Session = sessionmaker(bind=engine)

database = Session()

api_instance = LoginApi()

# FE6912: 251176 https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=abc493ca-87de-4730-bc61-c01ce7d76d27&state=FE6912&redirect_uri=http://localhost:8000/callback
# 42AFJE: 240220 https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=4386a770-aed7-4e7f-8cb2-663b778e4457&redirect_uri=https://account.upstox.com/contact-info/
# 6CAB9R: 006474 https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=2988abaa-c17e-4428-a43f-0fc7f22205b0&redirect_uri=https://account.upstox.com/contact-info/
# 6GALGR: 653278 https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=465ab58e-8e35-4b09-a289-e813d59d73f0&redirect_uri=https://account.upstox.com/contact-info/
# 2LCHHP: 653278 https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=8c9a6826-1b46-41a3-9492-7f3fe2d2ee71&redirect_uri=https://account.upstox.com/contact-info/

active_clients = database.query(Credentials).filter_by(is_active=TRUE)

for client in active_clients:
    client = database.query(Credentials).filter_by(client_id=client.client_id).first()

    try:
        api_response = api_instance.token(
            api_version="2.0",
            code=input(f"Enter the code for {client.client_id}: "),
            client_id=client.api_key,
            client_secret=client.api_secret,
            redirect_uri="https://account.upstox.com/contact-info/",
            grant_type="authorization_code",
        )
        client.access_token = api_response.access_token
        database.commit()
        print("Access Token Updated")
    except ApiException as e:
        print("Exception when calling LoginApi->token: %s\n" % e)

database.close()
