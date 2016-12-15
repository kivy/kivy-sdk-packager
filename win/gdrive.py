from os.path import join, isfile, dirname, basename
from os import listdir, environ
from glob import glob
from datetime import datetime, timedelta
from pydrive.auth import GoogleAuth
from apiclient import errors
from pydrive.drive import GoogleDrive

cred = 'my_cred'
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


def get_drive():
    with open('settings.yaml', 'wb') as fh:
        fh.write(settings)

    with open(cred, 'wb') as fh:
        fh.write(environ['AIRPLANE_CHARGE'].encode('ascii'))

    gauth = GoogleAuth()
    # gauth.LocalWebserverAuth()
    gauth.LoadCredentials()
    if gauth.access_token_expired:
        gauth.Refresh()

    drive = GoogleDrive(gauth)
    return drive


def get_files(folder_id, filters=''):
    drive = get_drive()
    l = drive.ListFile(
        {'q': "'{}' in parents and trashed=false".format(folder_id) + filters}).GetList()
    files = [item for item in l
             if item['mimeType'] != 'application/vnd.google-apps.folder']
    return drive, files


def get_filelist(folder_id):
    drive, files = get_files(folder_id)
    return drive, {item['title']: item['id'] for item in files}


def delete_older(folder_id, age):
    t = datetime.now() - timedelta(days=int(age))
    t = t.strftime('%Y-%m-%dT00:00:00')
    drive, files = get_files(folder_id, " and modifiedDate < '{}'".format(t))

    for item in files:
        try:
            print('Deleting {}'.format(item['title']))
            item.auth.service.files().delete(fileId=item['id']).execute()
        except Exception as e:
            print('An error occurred deleting "{}": {}'.format(item['title'], e))


def files_exist(folder_id, *names):
    drive, files = get_filelist(folder_id)
    return all([name in files for name in names])


def download_file(folder_id, directory, filename):
    drive, files = get_filelist(folder_id)
    if filename not in files:
        raise Exception("{} doesn't exist".format(filename))

    f = drive.CreateFile({'id': files[filename]})
    f.GetContentFile(join(directory, filename))


def upload_directory(folder_id, pat):
    drive, files = get_files(folder_id)
    files = {item['title']: item for item in files}

    for name in glob(pat):
        if not isfile(name):
            raise Exception('{} is not a file'.format(name))

        fname = basename(name)
        if fname in files and '.dev0' not in fname:
            print('Skipping {}. Already exists on gdrive'.format(fname))
            continue

        if fname in files:
            f = files[fname]
        else:
            f = drive.CreateFile({'parents': [{'id': folder_id}],
                                  'title': fname})
        f.SetContentFile(name)
        f.Upload()
        print('Uploaded {}'.format(f['title']))


if __name__ == '__main__':
    import sys
    cmd, folder_id = sys.argv[1:3]
    if cmd == 'upload':
        upload_directory(folder_id, sys.argv[3])
    elif cmd == 'delete_older':
        delete_older(folder_id, sys.argv[3])
    elif cmd == 'exists':
        print(files_exist(folder_id, *sys.argv[3:]))
    elif cmd == 'download':
        download_file(folder_id, *sys.argv[3:5])
