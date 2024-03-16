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