from pymongo import MongoClient
import hashlib
import secrets

mongo_client = MongoClient('mongo')
db = mongo_client['derp']
users = db['users']
authToken = db['auth_token']

def check_user_auth(token):
    if token is None:
        return False
    hash_object = hashlib.sha256(token.encode())
    hashed_token = hash_object.hexdigest()
    return authToken.find_one({"auth_token": hashed_token}) is not None

def generate_auth_token(username):
    generated_auth_token = secrets.token_hex(16)
    hash_object = hashlib.sha256(generated_auth_token.encode())
    hashed_auth_token = hash_object.hexdigest()

    authToken.find_one_and_delete({"username": username})
    authToken.insert_one({"username": username, "auth_token": hashed_auth_token})
    return generated_auth_token