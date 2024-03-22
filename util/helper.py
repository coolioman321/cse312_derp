def validate_password(password):
    # Length is at least 8
    if len(password) < 8:
        return False
    
    # Contains at least one lowercase letter
    if not any(c.islower() for c in password):
        return False
    
    #Contains at least one uppercase letter
    if not any(c.isupper() for c in password):
        return False
    
    #Contains at least one digit
    if not any(c.isdigit() for c in password):
        return False
    
    #Contains at least one special character
    if not any(c.isalnum() for c in password):
        return False
    
    return True

def escape_html(text):
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text

def read_file_as_byte(filename):
    with open (filename, "rb") as b_file:
        b_body = b_file.read()
        return b_body

import re
def extract_credentials(request_obj):
    print(request_obj)
    string_converted = (request_obj.body.decode())
    split_pairs_list = string_converted.split('&',1)
    unparsed_password = ""
    username = ""

    username_pair = split_pairs_list[0]
    username_pair_split = username_pair.split('=',1)
    username = username_pair_split[1]

    password_pair = split_pairs_list[1]
    password_pair_split = password_pair.split('=',1)
    unparsed_password = password_pair_split[1]
    unparsed_password = unparsed_password.replace("%28%27%2C+%27%29","(', ')")
    unparsed_password = unparsed_password.replace('+',' ')
    unparsed_password = unparsed_password.replace('%21','!')
    unparsed_password = unparsed_password.replace('%40','@')
    unparsed_password = unparsed_password.replace('%23','#')
    unparsed_password = unparsed_password.replace('%24','$')
    unparsed_password = unparsed_password.replace('%5E','^')
    unparsed_password = unparsed_password.replace('%26','&')
    unparsed_password = unparsed_password.replace('%3D','=')
    unparsed_password = unparsed_password.replace('%20',' ')
    unparsed_password = unparsed_password.replace('%2B','+')
    password = unparsed_password.replace('%25','%')

    return [username,password]

