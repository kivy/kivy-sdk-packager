import dropbox
from os.path import join
from os import listdir, environ


def upload_directory(directory):
    client = dropbox.client.DropboxClient(environ['PICKUPBOX_TOKEN'].encode('ascii'))

    for fname in listdir(directory):
        with open(join(directory, fname), 'rb') as fh:
            client.put_file('/{}'.format(fname), fh, overwrite=True)


if __name__ == '__main__':
    import sys
    upload_directory(sys.argv[1])
