import decimal
from falcon.status_codes import HTTP_200
from sqlalchemy import create_engine
from sqlalchemy.sql.expression import desc
from models import User, Route, Comment, UserRatedRoute, UserRatedComment, base
from sqlalchemy.orm import sessionmaker
import bcrypt
import datetime
import logging
import json
import falcon
import os
import jwt
import base64
from sys import platform
from constants import CONSTANTS
from falcon import media
from falcon_multipart.middleware import MultipartMiddleware

if platform == "win32":
    from waitress import serve


logger = logging.getLogger('bike_log')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('bike_logs.log')
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


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


host = 'localhost' if platform == 'win32' else 'localhost:5432'
dbname = 'bikeroutes' if platform == 'win32' else 'fablebike'

client = create_engine(
    'postgresql://' + CONSTANTS["DBUSER"] + ":" + CONSTANTS["DBPASS"] + '@' + host + '/' + dbname, echo=True)
base.metadata.create_all(bind=client)
session = sessionmaker(bind=client)

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

class AuthClass:
    def on_post_facebook(self, req, resp):
        try:
            data = req.media

            newUser = User()
            newUser.email = data["email"]
            newUser.name = data["user"]
            newUser.is_facebook = True

            s = session()

            expToken = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            timeStamp = str(int(expToken.timestamp()))
            hashedPassword = bcrypt.hashpw(
            timeStamp.encode('utf-8'), bcrypt.gensalt())
            newUser.password = hashedPassword.decode('ascii')

            existingUser = s.query(User).filter(User.name == newUser.name).first()
            if existingUser is not None:
                raise Exception('Exista deja un cont cu acest nume.')


            s.add(newUser)
            token = generate_user_token(newUser) if platform == 'win32' else generate_user_token(newUser).decode('utf-8')
            id = newUser.id
            s.commit()
            s.close()

            resp.status = HTTP_200
            resp.body = {"token": token, "user_id": id, "roles": "rw"}

        except(Exception) as e:
            logger.error("")
            resp.body = str(e)
            resp.status = falcon.HTTP_500

    def on_post_user_icon(self, req, resp):
        try:
            auth = verify_token(req.auth)

            chunk_size = 4096
            image = req.get_param('file')

            if req.content_length < 5000:
                image_path = os.path.join('images', image.filename)
            else:
                image_path = os.path.join('profile_images', image.filename)

            with open(image_path, 'wb') as image_file:
                while True:
                    chunk = image.file.read(chunk_size)
                    if not chunk:
                        break

                    image_file.write(chunk)

            s = session()
            user = s.query(User).filter(User.id == auth["user_id"]).first()
            user.icon = image.filename
            s.commit()

            resp.status = falcon.HTTP_200
            
        except(Exception) as e:
            logger.error("User Icon Post: " + str(e))
            resp.body = json.dumps({'message': e.message})
            resp.status = falcon.HTTP_500

    def on_get_user_icon(self, req, resp):
        try:
            auth = verify_token(req.auth)
            data = req.params

            path = os.path.join("images", data["imagename"])
            file_len = os.path.getsize(path)
            resp.content_type = "image/jpg"
            resp.set_stream(open(path, 'rb'), file_len)
                
        except(Exception) as e:
            logger.error("User Icon Get: " + str(e))
            resp.body = json.dumps({'message': e.message})
            resp.status = falcon.HTTP_500

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
                existingEmail = s.query(User).filter(User.email == user.email).first()
                if existingEmail is not None:
                    raise Exception('Exista deja un cont cu acest email.')
                
                existingUser = s.query(User).filter(User.name == user.name).first()
                if existingUser is not None:
                    raise Exception('Exista deja un cont cu acest nume.')

                s.add(user)
                s.commit()
                token = generate_user_token(user) if platform == 'win32' else generate_user_token(user).decode('utf-8')
                id = user.id
                s.close()

                resp.body = json.dumps({"token": token, "user_id": id, "roles": 'rw'})
                resp.status = falcon.HTTP_201  # 201 = CREATED
            except(Exception) as e:
                resp.body = str(e)
                resp.status = falcon.HTTP_400

        except(Exception) as e:
            logger.error("Auth Post: " + str(e))
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

                if user == None and username != 'GUEST':
                    resp.body = 'Utilizatorul nu exista.'
                    resp.status = falcon.HTTP_400
                elif username == 'GUEST':
                    token = generate_guest_token() if platform == 'win32' else generate_guest_token().decode('utf-8')
                    resp.body = json.dumps({'token': token})
                    resp.status = falcon.HTTP_202 
                elif bcrypt.checkpw(password, user.password.encode('utf-8')) or user.is_facebook == True:
                    rated_routes = []
                    rated_comments = []

                    for route in user.rated_routes:
                        rated_routes.append(route.id)

                    for comment in user.rated_comments:
                        rated_comments.append(comment.id)

                    token = generate_user_token(user) if platform == 'win32' else generate_user_token(user).decode('utf-8')
                    resp.body = json.dumps(
                        {'token': token, "user_id": user.id, 'user': user.name, 'icon': user.icon, 'rated_routes': rated_routes, 'rated_comments': rated_comments, 'roles': user.roles})
                    resp.status = falcon.HTTP_202  # 202 = Accepted
                else:
                    resp.body = 'Datele de autentificare sunt gresite.'
                    resp.status = falcon.HTTP_400

        except(Exception) as e:
            logger.error("Auth get: " + str(e))
            resp.body = 'Probleme la autentificare.'
            resp.status = falcon.HTTP_400


class CommentClass:
    def on_get(self, req, resp):
        try:
            auth = verify_token(req.auth)
            data = req.params

            route_id = int(data["route_id"])
            page = int(data["page"])

            if page < 0 or route_id < 0 or route_id > 25:
                raise falcon.HTTPBadRequest(
                    title="Params out of range",
                    description="Invalid data, possible threat."
                )

            with client.connect() as con:
                comments = con.execute("SELECT c.id, c.text, c.user, c.route_id, c.rating, c.created_on, u.icon, u.id as user_id FROM public.comment c INNER JOIN public.user u ON u.name = c.user WHERE route_id = " +
                                       str(route_id) + " ORDER BY created_on DESC LIMIT 5 OFFSET " + str(page) + " * 5;")
                row_count = con.execute("Select COUNT(*) FROM public.comment WHERE route_id = " + str(route_id) + ";")

            comment_list = []
            comment_count = 0
            for row in row_count:
                comment_count = row["count"]

            for row in comments:
                comment_list.append(
                    {"id": row["id"], "icon": row["icon"], "user_id": row["user_id"], "text": row["text"], "user": row["user"], "route_id": row["route_id"]})

            resp.body = json.dumps(
                {"page": page, "comment_count": comment_count, "comments": comment_list})
            resp.status = falcon.HTTP_200
        except(Exception) as e:
            logger.error("Comment get: " + str(e))
            resp.body = 'Comment can not be retrieved.'
            resp.status = falcon.HTTP_400

    def on_post_rate(self, req, resp):
        try:
            auth = verify_token(req.auth)
            data = req.media

            comment_id = int(data["comment_id"])

            s = session()
            commentRate = s.query(UserRatedComment).filter(
                UserRatedComment.id == auth["id"]).first()

            comment = s.query(Comment).filter(Comment.id == comment_id).first()

            if commentRate is None:
                comment.rating += 1
                newCommentRate = UserRatedComment()
                newCommentRate.user_id = auth["user_id"]
                newCommentRate.comment_id = comment_id
                s.add(newCommentRate)
            else:
                comment.rating -= 1

            s.commit()
            s.close()

            resp.status = falcon.HTTP_200
        except(Exception) as e:
            resp.body = 'Comentariul nu a putut fi postat.'
            logger.error("Comment rate: " + str(e))
            resp.status = falcon.HTTP_400

    def on_post(self, req, resp):
        try:
            auth = verify_token(req.auth)

            data = req.media
            comment = Comment()
            comment.user_id = auth["user"]
            comment.text = data["text"]
            comment.route_id = int(data["route_id"])
            created_on = datetime.datetime.utcnow()
            comment.created_on = created_on

            s = session()
            s.add(comment)
            s.flush()

            id = comment.id
            s.commit()
            s.close()

            resp.body = json.dumps(
                {"id": id, "text": data["text"], "user": auth["user"], "user_id": auth["user_id"], "route_id": int(data["route_id"])})
            resp.status = falcon.HTTP_201

        except(Exception) as e:
            resp.body = 'Comentariul nu a putut fi postat.'
            logger.error("Comment post: " + str(e))
            resp.status = falcon.HTTP_400


class RouteClass():
    def on_post(self, req, resp):
        try:
            auth = verify_token(req.auth)

            data = req.media

            route_id = int(data["route_id"])
            rating = int(data["rating"])

            routeRating = UserRatedRoute()
            routeRating.user_id = auth["user_id"]
            routeRating.route_id = route_id

            s = session()

            dbRouteRating = s.query(UserRatedRoute).filter(
                UserRatedRoute.user_id == auth["user_id"]).filter(UserRatedRoute.route_id == route_id).first()

            if dbRouteRating is not None:
                raise falcon.HTTPBadRequest(title="User already voted", description="User" +
                                            str(auth["user_id"]) + " already voted for route: " + str(data["route_id"]))

            route = s.query(Route).filter(Route.id == route_id).first()
            if rating == 1:
                route.one_star += 1
            if rating == 2:
                route.two_star += 1
            if rating == 3:
                route.three_star += 1
            if rating == 4:
                route.four_star += 1
            if rating == 5:
                route.five_star += 1

            rating = (route.one_star + route.two_star * 2 + route.three_star * 3 + route.four_star * 4 + route.five_star *
                      5) / (route.one_star + route.two_star + route.three_star + route.four_star + route.five_star)
            route.rating = rating
            s.add(routeRating)
            s.commit()
            s.close()

            resp.status = falcon.HTTP_200
            resp.body = json.dumps({"rating": rating})
        except(Exception) as e:
            logger.error("Route post: " + str(e))
            resp.body = 'Failed'
            resp.status = falcon.HTTP_400

    def on_get(self, req, resp):
        try:
            verify_token(req.auth)

            data = req.params
            route_id = int(data["route_id"])
            comment_count = 0

            s = session()
            route = s.query(Route).filter(Route.id == route_id).first()
            ratingCount = route.one_star + route.two_star + route.three_star + route.four_star + route.five_star
            comment_count = s.query(Comment).filter(Comment.route_id == route_id).count()
            s.close()

            resp.status = falcon.HTTP_200
            resp.body = json.dumps(
                {"route": route.name, "rating": route.rating, "rating_count": ratingCount, "commentCount": comment_count})
        except(Exception) as e:
            resp.status = falcon.HTTP_400
            resp.body = 'Failed'
            logger.error('Route get: ' + str(e))


app = falcon.API(middleware=[MultipartMiddleware()])
app.add_route('/auth', AuthClass())
app.add_route('/auth/user_icon', AuthClass(), suffix='user_icon')
app.add_route('/auth/sign_up', AuthClass(), suffix='sign_up')
app.add_route('/auth/facebook', AuthClass(), suffix='facebook')
app.add_route('/comment', CommentClass())
app.add_route('/comment/rate', CommentClass(), suffix='rate')
app.add_route('/route', RouteClass())


if platform == "win32":
    serve(app, listen='0.0.0.0:8080')
