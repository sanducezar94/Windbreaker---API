from enum import auto
import json, falcon, jwt, base64
from sqlalchemy import create_engine, Column, Integer,Text, String, ForeignKey
import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import text
import psycopg2, bcrypt, datetime
from sqlalchemy.sql.sqltypes import DateTime
from waitress import serve;


CONSTANTS = {
    'SECRET': 's#sec3rt',
    'CRED_SECRET': 'sagasaga',
    "ALGORITHMS": ['HS256']
}

base = declarative_base()

def validate_jwt(token, secret):
    try:
        return jwt.decode(token, secret, CONSTANTS['ALGORITHMS'])
    except:
        raise jwt.DecodeError()


class User(base):
    __tablename__ = "user"

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(80), unique=True)
    email = Column('email',String(256),  unique=True)
    password = Column('password', Text)


client = create_engine('postgresql://postgres:Markerlel20@localhost/bikeroutes', echo=True)
base.metadata.create_all(bind=client)
session = sessionmaker(bind=client)

def generate_user_token(user):
    expToken = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    expTokenInt = int(expToken.timestamp())
    token = jwt.encode({
        'username': user.email,
        'exp': expTokenInt,
        'iat': int(datetime.datetime.utcnow().timestamp())
    }, CONSTANTS['SECRET'])
    return token

class AuthClass:
    def on_post(self, req, resp):
        try:
            data = req.media
            
        except(Exception):
            raise falcon.HTTPInternalServerError
    
    def on_post_sign_up(self, req, resp):
        try: 
            data = req.media
            user = User()
            user.name = data['user']
            user.email = data['email']

            hashedPassword = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
            user.password = hashedPassword.decode('ascii')

            try:
                s = session()
                s.add(user)
                token = generate_user_token(user)
                s.commit()
                s.close()

                resp.body = json.dumps(token)
                resp.status = falcon.HTTP_201 #201 = CREATED
            except(Exception) as e:
                resp.body = 'Exista deja un cont cu acest email.'
                resp.status = falcon.HTTP_400


        except(Exception) as e:
            resp.body = json.dumps({'message': e.message})
            resp.status = falcon.HTTP_500

    def on_get(self, req, resp):
        try:
            auth_exp = req.auth.split(' ') if req.auth is not None else (None, None)

            if auth_exp[0].lower() == 'basic':
                auth = base64.b64decode(auth_exp[1]).decode('utf-8').split(':')

                username = auth[0]
                password = auth[1].encode('utf-8')

                s = session()
                user = s.query(User).filter(User.email == username).first()
                s.close()

                if user is None:
                    resp.body = 'Utilizatorul nu exista.'
                    resp.status = falcon.HTTP_400
                elif bcrypt.checkpw(password, user.password.encode('utf-8')):
                    resp.body = generate_user_token(user)
                    resp.status = falcon.HTTP_202 #202 = Accepted
                else:
                    resp.body = 'Datele de autentificare sunt gresite.'
                    resp.status = falcon.HTTP_400

        except(Exception) as e:
            print(e.message)

class CommentsClass:
    def on_post(self, req, resp):
        auth_exp = req.auth


api = falcon.API()
api.add_route('/auth', AuthClass())
api.add_route('/auth/sign_up', AuthClass(), suffix='sign_up')

serve(api, listen='0.0.0.0:8080')