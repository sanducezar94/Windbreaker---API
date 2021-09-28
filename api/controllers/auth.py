from api.constants import CONSTANTS
from falcon.status_codes import HTTP_200, HTTP_400
import bcrypt, datetime, json, falcon, os, base64, zipfile
from sys import platform


from api import logger, client, session, limiter, generate_user_token, generate_guest_token, verify_token
from api.models import User
from api.helpers.validators import validateOAuthSignUp, validateSignUp
from api.helpers.oauth_validators import validateFacebookToken

def checkUserAndPassword(user, password, oauth_validated):
    if user == None: 
        return False
    if bcrypt.checkpw(password, user.password.encode('utf-8')) or (user.is_facebook == True and oauth_validated == True):
        return True
    return False

def getLoginData():
    data = {'routes': [], 'objectives': []}

    with client.connect() as con:
        objectiveRows = con.execute("SELECT id, rating, rating_count FROM public.objective")
        routeRows = con.execute("SELECT id, rating, rating_count FROM public.route")

        for obj in objectiveRows:
            data['objectives'].append({'id': obj['id'], 'rating': obj['rating'], 'rating_count': obj['rating_count']})
        
        for route in routeRows:
            data['routes'].append({'id': route['id'], 'rating': route['rating'], 'rating_count': route['rating_count']})
    
    return data

class AuthClass:
    @limiter.limit()
    def on_post_facebook(self, req, resp):
        try:
            data = req.media

            newUser = User()
            newUser.email = data["email"].strip()
            newUser.name = data["user"].strip()
            userToken = data["user_token"].strip()

            validateOAuthSignUp(newUser.name, newUser.email)
            validateFacebookToken(userToken)
            newUser.is_facebook = True

            s = session()

            expToken = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            timeStamp = str(int(expToken.timestamp()))
            hashedPassword = bcrypt.hashpw(timeStamp.encode('utf-8'), bcrypt.gensalt())
            newUser.password = hashedPassword.decode('ascii')

            existingUser = s.query(User).filter(User.name == newUser.name).first()
            if existingUser is not None:
                raise Exception('Exista deja un cont cu acest nume.')


            s.add(newUser)
            s.commit()
            token = generate_user_token(newUser)
            id = newUser.id
            s.close()

            loginData = getLoginData()

            resp.status = HTTP_200
            resp.body = json.dumps({"token": token, "login_data": json.dumps(loginData), "user_id": id, "roles": "rw"})

        except(Exception) as e:
            logger.error("")
            resp.body = str(e)
            resp.status = falcon.HTTP_500

    @limiter.limit()
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

    @limiter.limit()
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

    @limiter.limit()
    def on_get_icons_zip(self, req, resp):
        try:
            #auth = verify_token(req.auth)
            #data = req.params

            files = ['hope.jpg', 'hope1.jpg', 'hope2.jpg']

            with zipfile.ZipFile('icons.zip', 'w') as zipF:
                for f in files:
                    zipF.write('images/' + f, compress_type=zipfile.ZIP_DEFLATED)
                    #path = os.path.join("images", data["imagename"])

            file_len = os.path.getsize('icons.zip')
            resp.content_type = "multipart/form-data"
            resp.set_stream(open('icons.zip', 'rb'), file_len)
                
        except(Exception) as e:
            logger.error("User Icon Get: " + str(e))
            resp.body = json.dumps({'message': e.message})
            resp.status = falcon.HTTP_500

    @limiter.limit()
    def on_post_sign_up(self, req, resp):
        try:
            data = req.media
            user = User()
            user.name = data['user'].strip()
            user.email = data['email'].strip()

            validateSignUp(user.name, user.email, data['password'])

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
                token = generate_user_token(user)
                id = user.id
                s.close()

                loginData = getLoginData()

                resp.body = json.dumps({"token": token, "login_data": json.dumps(loginData), "user_id": id, "roles": 'rw'})
                resp.status = falcon.HTTP_201  # 201 = CREATED
            except(Exception) as e:
                resp.body = str(e)
                resp.status = falcon.HTTP_400

        except(Exception) as e:
            logger.error("Auth Post: " + str(e))
            resp.body = json.dumps({'message': e.message})
            resp.status = falcon.HTTP_500

    @limiter.limit()
    def on_get_persistent(self, req, resp):
        try:
            auth = verify_token(req.auth)
            email = auth["user"]

            s = session()
            user = s.query(User).filter(User.email == email).first()
            s.close()

            if user == None:
                resp.status = falcon.HTTP_401
            else:
                token = generate_user_token(user)
                loginData = getLoginData()

                resp.body = json.dumps(
                    {'token': token, 'id': user.id, 'email': email, 'username': user.name, 'icon': user.icon, 'distanceTravelled': user.distance_travelled, 'finishedRoutes': user.routes_finished, 'objectivesVisited': user.objectives_visited, 'login_data': json.dumps(loginData)})
                resp.status = falcon.HTTP_200
        except(Exception) as e:
            logger.error("Auth error")

    @limiter.limit(deduct_when=lambda req, resp, resource, req_succeeded: resp.status != falcon.HTTP_500)
    def on_get(self, req, resp):
        try:
            auth_exp = req.auth.split(
                ' ') if req.auth is not None else (None, None)

            if auth_exp[0].lower() == 'basic':
                auth = base64.b64decode(auth_exp[1]).decode('utf-8').split(':')
                email = auth[0]
                password = auth[1].encode('utf-8')

                s = session()
                user = s.query(User).filter(User.email == email).first()
                s.close()

                if checkUserAndPassword(user, password, False) == True:
                    token = generate_user_token(user)
                    loginData = getLoginData()

                    resp.body = json.dumps(
                        {'token': token, "login_data": loginData, "id": user.id, email: email, 'username': user.name, 'icon': user.icon, 'distanceTravelled': user.distance_travelled, 'finishedRoutes': user.routes_finished, 'objectivesVisited': user.objectives_visited})
                    resp.status = falcon.HTTP_200  # 202 = Accepted
                else:
                    raise Exception('Email sau parola incorectă.')

        except(Exception) as e:
            logger.error("Auth get: " + str(e))
            resp.body = str(e)
            resp.status = falcon.HTTP_400

    @limiter.limit(deduct_when=lambda req, resp, resource, req_succeeded: resp.status != falcon.HTTP_500)
    def on_get_oauth(self, req, resp):
        try:
            auth_exp = req.auth.split(
                ' ') if req.auth is not None else (None, None)

            if auth_exp[0].lower() == 'basic':
                auth = base64.b64decode(auth_exp[1]).decode('utf-8').split(':')
                email, password = auth[0], auth[1].encode('utf-8')
                oauth_validated, data = False, req.params
                if data is not None:
                    token, provider = data["oauth_token"], data["provider"]
                    
                    if provider == 'FACEBOOK':
                        oauth_validated = validateFacebookToken(token, 0)
                    else:
                        oauth_validated = validateFacebookToken(token, 0)
                    if oauth_validated == False:
                        raise Exception('Conexiunea nu a putut fi realizata')
                else:
                    raise Exception('Conexiunea nu a putut fi realizata')

                s = session()
                user = s.query(User).filter(User.email == email).first()
                s.close()

                if checkUserAndPassword(user, password, True) == True:
                    token = generate_user_token(user)
                    loginData = getLoginData()
                    resp.body = json.dumps(
                        {'token': token, "login_data": loginData, "id": user.id, email: email, 'username': user.name, 'icon': user.icon, 'distanceTravelled': user.distance_travelled, 'finishedRoutes': user.routes_finished, 'objectivesVisited': user.objectives_visited})
                    resp.status = falcon.HTTP_200  # 202 = Accepted
                else:
                    raise Exception('Email sau parola incorectă.')


        except(Exception) as e:
            logger.error("Auth get: " + str(e))
            resp.body = str(e)
            resp.status = falcon.HTTP_400
