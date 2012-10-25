DEBUG_MODE = False

MANAGERS = (
    'OVERRIDE-ME-IN-LOCAL-SETTINGS',
)

MAIL_USER = 'OVERRIDE-ME-IN-LOCAL-SETTINGS'
MAIL_PASSWORD = 'OVERRIDE-ME-IN-LOCAL-SETTINGS'


# Local settings for easy developement
try:
    from local_settings import *
except:
    pass
