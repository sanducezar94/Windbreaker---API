from api.constants import CONSTANTS
from falcon.status_codes import HTTP_200, HTTP_400
import bcrypt, datetime, json, falcon, os, base64, zipfile
from sys import platform


from api import logger, client, session, limiter, verify_token
from api.models import User, Otp
from api.helpers.validators import validateEmail
from api.helpers.email_sender import send_otp



class OtpClass:
    @limiter.limit()
    def on_get(self, req, resp):
        try:
            data = req.params
            email = data['email']
            validateEmail(email)

            send_otp(email)
            time_now = datetime.datetime.utcnow()
            resp.body = json.dumps({'date_sent': str(time_now)})
            resp.status = falcon.HTTP_200
        except(Exception) as e:
            resp.body = str(e)
            resp.status = falcon.HTTP_500

    @limiter.limit()
    def on_post(self, req, resp):
        try:
            #auth = verify_token(req.auth)
            email = req.media['email']
            otp_code = req.media['otp']
            resp.status = falcon.HTTP_200

            s = session()
            otp = s.query(Otp).filter(Otp.email == email).filter(Otp.key == otp_code).first()

            if otp is None or otp.key != otp_code:
                raise Exception('Codul este invalid.')

            if otp.created_on < datetime.datetime.utcnow() - datetime.timedelta(seconds=90):
                raise Exception('Codul a expirat.')

            s.delete(otp)
            s.commit()
            resp.body = json.dumps({'success': True})
            resp.status = falcon.HTTP_200

        except(Exception) as e:            
            logger.error("Otp get: " + str(e))
            resp.body = str(e)
            resp.status = falcon.HTTP_400
