from api.constants import CONSTANTS
import requests

from api import session
from api.models import SystemValue

def getFacebookToken():
    url = 'https://graph.facebook.com/oauth/access_token?client_id={1}&client_secret={2}&grant_type=client_credentials'

    url = url.replace('{1}', CONSTANTS['APP_ID'])
    url = url.replace('{2}', CONSTANTS['APP_SECRET'])

    response = requests.get(url)

    if response.status_code == 200:
        body = response.json()
        s = session()
        token = body['access_token']
        fbToken = SystemValue()
        fbToken.key = 'fb_token'
        fbToken.value = token
        s.add(fbToken)
        s.commit()
        s.close()

        return body['access_token']
    
    return ''

def validateFacebookToken(userToken, tryNumber):
    try:
        if tryNumber >= 2:
            return False

        url = 'https://graph.facebook.com/debug_token?input_token={1}&access_token={2}'

        s = session()
        token = s.query(SystemValue).filter(SystemValue.key == 'fb_token').first()
        fbToken = ''

        if token is None:
            fbToken = getFacebookToken()
        else: 
            fbToken = token.value

        url = url.replace('{1}', userToken)
        url = url.replace('{2}', fbToken)

        response = requests.get(url)

        if response.status_code == 200:
            s.close()
            return True
        else:
            s.delete(token)
            s.commit()
            s.close()
            getFacebookToken()
            return validateFacebookToken(userToken, tryNumber + 1)
    except(Exception) as e:
        return False