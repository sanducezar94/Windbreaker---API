from falcon.status_codes import HTTP_200, HTTP_400
from sqlalchemy import create_engine
from sqlalchemy.sql.expression import desc
from api.models import Route, base
from sqlalchemy.orm import sessionmaker
import datetime, logging, json, jwt, falcon
from sys import platform
from api.constants import CONSTANTS
from falcon_multipart.middleware import MultipartMiddleware
from falcon_limiter import Limiter
from falcon_limiter.utils import get_remote_addr

logger = logging.getLogger('bike_log')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('bike_logs.log')
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

limiter = Limiter(
    key_func=get_remote_addr,
    default_limits="5 per minute, 4 per second"
)

host = 'localhost' if platform == 'win32' else 'localhost:5432'
dbname = 'bikeroutes' if platform == 'win32' else 'fablebike'

client = create_engine(
    'postgresql://' + CONSTANTS["DBUSER"] + ":" + CONSTANTS["DBPASS"] + '@' + host + '/' + dbname, echo=False)
base.metadata.create_all(bind=client)
session = sessionmaker(bind=client)

def verify_token(auth):
    auth_exp = auth.split(' ') if auth is not None else (None, None)

    try:
        if auth_exp is (None, None):
            raise jwt.MissingRequiredClaimError()

        if auth_exp[0].lower() == 'bearer':
            try:
                return jwt.decode(auth_exp[1], CONSTANTS['SECRET'], CONSTANTS["ALGORITHM"])
            except:
                raise jwt.DecodeError()
    except(Exception) as e:
        raise jwt.DecodeError()


def verify_token(auth):
    auth_exp = auth.split(' ') if auth is not None else (None, None)

    try:
        if auth_exp is (None, None):
            raise jwt.MissingRequiredClaimError()

        if auth_exp[0].lower() == 'bearer':
            try:
                return jwt.decode(auth_exp[1], CONSTANTS['SECRET'], CONSTANTS["ALGORITHM"])
            except:
                raise jwt.DecodeError()
    except(Exception) as e:
        raise jwt.DecodeError()


def generate_user_token(user):
    expToken = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    expTokenInt = int(expToken.timestamp())
    token = jwt.encode({
        'user': user.name,
        'user_id': user.id,
        'exp': expTokenInt,
    }, CONSTANTS['SECRET'], CONSTANTS["ALGORITHM"])
    return token

def generate_guest_token():
    expToken = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    expTokenInt = int(expToken.timestamp())
    token = jwt.encode({
        'user': 'GUEST',
        'user_id': -1,
        'exp': expTokenInt,
    }, CONSTANTS['SECRET'], CONSTANTS["ALGORITHM"])
    return token

def initialize():
    try:
        s = session()
        routeCount = s.query(Route).count()
        if routeCount == 0:
            f = open('initial_data.json')
            jsonData = json.load(f)

            for data in jsonData:
                newRoute = Route()
                newRoute.id = data["id"]
                newRoute.name = data["name"]
                s.add(newRoute)
        s.commit()
        s.close()
    except(Exception) as e:
        logger.error("Problema initializing: " + str(e))

initialize()


from api.controllers.auth import AuthClass
from api.controllers.comment import CommentClass
from api.controllers.route import RouteClass
from api.controllers.objective import ObjectiveClass


app = falcon.API(middleware=[MultipartMiddleware(), limiter.middleware])
app.add_route('/api/fablebike/auth', AuthClass())
app.add_route('/api/fablebike/auth/oauth', AuthClass(), suffix='oauth')
app.add_route('/api/fablebike/auth/persistent', AuthClass(), suffix='persistent')
app.add_route('/api/fablebike/auth/user_icon', AuthClass(), suffix='user_icon')
app.add_route('/api/fablebike/auth/icons_zip', AuthClass(), suffix='icons_zip')
app.add_route('/api/fablebike/auth/sign_up', AuthClass(), suffix='sign_up')
app.add_route('/api/fablebike/auth/facebook', AuthClass(), suffix='facebook')
app.add_route('/api/fablebike/comment', CommentClass())
app.add_route('/api/fablebike/comment/rate', CommentClass(), suffix='rate')
app.add_route('/api/fablebike/route', RouteClass())
app.add_route('/api/fablebike/objective', ObjectiveClass())