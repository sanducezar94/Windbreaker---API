from enum import auto
import json
import falcon
import jwt
import logging
import base64
from sqlalchemy import create_engine, Column, Integer, Text, Numeric, String, ForeignKey
import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import bcrypt
import datetime
from sqlalchemy.sql.sqltypes import DateTime
#from waitress import serve


CONSTANTS = {
    'SECRET': 's#sec3rt',
    'CRED_SECRET': 'sagasaga',
    "ALGORITHM": 'HS256'
}

logger = logging.getLogger('bike_log')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('bike_logs.log')
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


base = declarative_base()

def verify_token(auth):
    return True
    auth_exp = auth.split(' ') if auth is not None else (None, None)

    if auth_exp[0].lower() == 'basic':
        token = base64.b64decode(auth_exp[1]).decode('utf-8')
        
        try:
            return jwt.decode(token, CONSTANTS['SECRET'])
        except:
            raise jwt.DecodeError()


class User(base):
    __tablename__ = "user"

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(80), unique=True)
    email = Column('email', String(128),  unique=True)
    password = Column('password', String(128))


class Route(base):
    __tablename__ = "route"

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String(80))
    rating = Column('rating', Numeric)
    comments = relationship("Comment", back_populates="parent")


class Comment(base):
    __tablename__ = "comment"

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    text = Column('text', String(128))
    user_id = Column('user_id', Integer, ForeignKey('user.id'))
    route_id = Column('post_id', Integer, ForeignKey('route.id'))
    parent = relationship("Route", back_populates="comments")


client = create_engine(
    'postgresql://postgres:Markerlel20@localhost/bikeroutes', echo=True)
base.metadata.create_all(bind=client)
session = sessionmaker(bind=client)

print('TEST')
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

            hashedPassword = bcrypt.hashpw(
                data['password'].encode('utf-8'), bcrypt.gensalt())
            user.password = hashedPassword.decode('ascii')

            try:
                s = session()
                s.add(user)
                token = generate_user_token(user)
                s.commit()
                s.close()

                resp.body = token
                resp.status = falcon.HTTP_201  # 201 = CREATED
            except(Exception) as e:
                resp.body = 'Exista deja un cont cu acest email.'
                resp.status = falcon.HTTP_400

        except(Exception) as e:
            resp.body = json.dumps({'message': e.message})
            resp.status = falcon.HTTP_500

    def on_get(self, req, resp):
        try:
            auth_exp = req.auth.split(
                ' ') if req.auth is not None else (None, None)

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
                    resp.status = falcon.HTTP_202  # 202 = Accepted
                else:
                    resp.body = 'Datele de autentificare sunt gresite.'
                    resp.status = falcon.HTTP_400

        except(Exception) as e:
            print(e.message)


class CommentClass:
    def on_post(self, req, resp):
        try:
            auth = verify_token(req.auth)

            data = req.media()
            comment = Comment()
            comment.user_id = auth["user_id"]
            comment.text = data["text"]
            comment.route_id = data["route_id"]

            s = session()
            s.add(comment)
            s.close()

            resp.body = 'Posted'
            resp.status = falcon.HTTP_201

        except(Exception) as e:
            resp.body = 'Failed'
            resp.status = falcon.HTTP_400

    def on_get(self, req, resp):
        try:
            auth = verify_token(req.auth)

            data = req.params.items()
            s = session()
            comments = s.query(Comment).filter(Comment.route_id == 1).paginate(0, data["per_page"], error_out=False)
            s.close()

        except(Exception) as e:
            resp.body = 'Failed'
            resp.status = falcon.HTTP_400


api = falcon.API()
api.add_route('/auth', AuthClass())
api.add_route('/auth/sign_up', AuthClass(), suffix='sign_up')
api.add_route('/comment', CommentClass())

serve(api, listen='0.0.0.0:8080')
