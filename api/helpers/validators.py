
import re

def validateEmail(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    let = re.match(regex, email)
    if re.match(regex, email):
        return True
    else:
        raise Exception('Email-ul nu este valid.')

def validateUser(user):
    regex = r'\b\s+\b'
    if len(user) < 4:
        raise Exception('Numele de utilizator nu poate fi mai scurt de 4 caractere.')
    if re.match(regex, user):
        raise Exception('Numele de utilizator nu poate contine spatii sau caractere speciale.')
    else:
        return True

def validateOAuthSignUp(user, email):
    if validateEmail(email) == False or validateUser(user) == False:
        return False

    return True


def validateSignUp(user, email, password):
    if validateEmail(email) == False or validateUser(user) == False:
        return False
    
    return True