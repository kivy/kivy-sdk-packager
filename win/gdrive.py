from os.path import join, isfile, dirname
from os import listdir, environ
from pydrive.auth import GoogleAuth
from apiclient import errors
from pydrive.drive import GoogleDrive

cred = join(dirname(__file__), 'my_cred')
settings = b'''
client_config_backend: settings
client_config:
  client_id: {}
  client_secret: {}
  auth_uri: https://accounts.google.com/o/oauth2/auth
  token_uri: https://accounts.google.com/o/oauth2/token
  redirect_uri: http://localhost:8080/

save_credentials: True
save_credentials_file: {}
save_credentials_backend: file
get_refresh_token: True
'''.format(environ['GDRIVE_CLIENT_ID'].encode('ascii'),
           environ['GDRIVE_CLIENT_SECRET'].encode('ascii'), cred)


def upload_directory(directory):
    with open(join(dirname(__file__), 'settings.yaml'), 'wb') as fh:
        fh.write(settings)

    with open(cred, 'wb') as fh:
        fh.write(environ['AIRPLANE_CHARGE'].encode('ascii'))

    gauth = GoogleAuth()
    # gauth.LocalWebserverAuth()
    gauth.LoadCredentials()
    if gauth.access_token_expired:
        gauth.Refresh()

    drive = GoogleDrive(gauth)

    for fname in listdir(directory):
        name = join(directory, fname)
        if not isfile(name):
            raise Exception('{} is not a file'.format(name))

        f = drive.CreateFile({'parents': [{'id': environ['GDRIVE_UPLOAD_ID']}],
                              'title': fname})
        f.SetContentFile(name)
        f.Upload()
        print('Uploaded {}'.format(f['title']))

#     try:
#         gauth.service.files().delete(fileId='0B1_HB9J8mZepdHFWaDB5VjJFQWM').execute()
#     except errors.HttpError, error:
#         print 'An error occurred: %s' % error


if __name__ == '__main__':
    import sys
    upload_directory(sys.argv[1])
