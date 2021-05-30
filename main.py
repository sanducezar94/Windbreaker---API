from sqlalchemy import create_engine
from models import User, Route, Comment, UserRatedRoute, UserRatedComment, base
from sqlalchemy.orm import sessionmaker
import bcrypt, datetime, logging, json, falcon, jwt, base64
from sys import platform
from constants import CONSTANTS

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
    expToken = datetime.datetime.utcnow()# + datetime.timedelta(hours=24)
    expTokenInt = int(expToken.timestamp())
    token = jwt.encode({
        'user': user.name,
        'user_id': user.id,
        'exp': expTokenInt,
    }, CONSTANTS['SECRET'], CONSTANTS["ALGORITHM"])
    return token


host = 'localhost' if platform == 'win32' else 'localhost:5432'

client = create_engine(
    'postgresql://' + CONSTANTS["DBUSER"] + ":" + CONSTANTS["DBPASS"] + '@' + host + '/bikeroutes', echo=True)
base.metadata.create_all(bind=client)
session = sessionmaker(bind=client)


class AuthClass:
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
            logger.log("Auth Post: " + e)
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

                if user == None:
                    resp.body = 'Utilizatorul nu exista.'
                    resp.status = falcon.HTTP_400
                elif bcrypt.checkpw(password, user.password.encode('utf-8')):
                    rated_routes = []
                    rated_comments = []

                    for route in user.rated_routes:
                        rated_routes.append(route.id)
                    
                    for comment in user.rated_comments:
                        rated_comments.append(comment.id)

                    resp.body = json.dumps(
                        {'token': generate_user_token(user), 'user': user.name, 'rated_routes': rated_routes, 'rated_comments': rated_comments})
                    resp.status = falcon.HTTP_202  # 202 = Accepted
                else:
                    resp.body = 'Datele de autentificare sunt gresite.'
                    resp.status = falcon.HTTP_400

        except(Exception) as e:
            logger.log("Auth get: " + e)
            resp.body = 'Probleme la autentificare.'
            resp.status = falcon.HTTP_400

class CommentClass:
    def on_post_rate(self, req, resp):
        try:
            auth = verify_token(req.auth)
            data = req.media

            comment_id = int(data["comment_id"])
            rating = int(data["rating"])

            s = session()
            commentRate = s.query(UserRatedComment).where(UserRatedComment.id == auth["id"]).first()
            s.query(Comment).filter(Comment.id == comment_id).update({})
            s.update(Comment).where
        except(Exception) as e:
            resp.body = falcon.HTTP_400

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

            id = 0

            s = session()
            s.add(comment)
            s.flush()

            id = comment.id
            s.commit()
            s.close()

            resp.body = json.dumps({"id": id, "text": data["text"], "user": auth["user"], "route_id": int(data["route_id"])})
            resp.status = falcon.HTTP_201

        except(Exception) as e:
            resp.body = 'Comentariul nu a putut fi postat.'
            logger.log("Comment post: " + e)
            resp.status = falcon.HTTP_400

    def on_get(self, req, resp):
        try:
            verify_token(req.auth)

            data = req.params

            route_id = data["route_id"]
            page = data["page"]

            with client.connect() as con:
                comments = con.execute("SELECT * FROM public.comment WHERE route_id = " +
                                       route_id + " ORDER BY created_on DESC LIMIT 10 OFFSET " + page + " * 10;")

            comment_list = []

            for row in comments:
                comment_list.append(
                    {"id": row["id"], "text": row["text"], "user": row["user"], "route_id": row["route_id"]})

            resp.body = json.dumps({"page": page, "comments": comment_list})
            resp.status = falcon.HTTP_200

        except(Exception) as e:
            logger.log("Comment get: " + e)
            resp.body = 'Failed'
            resp.status = falcon.HTTP_400

class RouteClass():
    def on_post(self, req, resp):
        try:
            token = verify_token(req.auth)

            data = req.media

            route_id = int(data["route_id"])
            rating = int(data["rating"])

            routeRating = UserRatedRoute()
            routeRating.user_id = token["user_id"]
            routeRating.route_id = route_id

            s = session()
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

            rating = (route.one_star + route.two_star * 2 + route.three_star * 3 + route.four_star * 4 + route.five_star * 5) / (route.one_star + route.two_star + route.three_star + route.four_star + route.five_star)
            route.rating = rating
            s.add(routeRating)
            s.commit()
            s.close()

            resp.status = falcon.HTTP_200
            resp.body = json.dumps({"rating": rating})
        except(Exception) as e:
            logger.log("Route post: " + e)
            resp.body = 'Failed'
            resp.status = falcon.HTTP_400

    def on_get(self, req, resp):
        try:
            verify_token(req.auth)

            data = req.params
            route_id = int(data["route_id"])

            s = session()
            route = s.query(Route).filter(Route.id == route_id).first()
            s.close()

            resp.status = falcon.HTTP_200
            resp.body = json.dumps({"route": route.name, "rating": float(route.rating)})
        except(Exception) as e:
            resp.status = falcon.HTTP_400
            resp.body = 'Failed'
            logger.log('Route post: ' + e)




app = falcon.API()
app.add_route('/auth', AuthClass())
app.add_route('/auth/sign_up', AuthClass(), suffix='sign_up')
app.add_route('/comment', CommentClass())
app.add_route('/comment/rate', CommentClass(), suffix='rate')
app.add_route('/route', RouteClass())

if platform == "win32":
    serve(app, listen='0.0.0.0:8080')
