from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']


def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    drive_service = build('drive', 'v3', credentials=creds)


    # Call the Drive v3 API
    results = drive_service.files().list(
        pageSize=10,
        q="'112V1rDMqEyWGeSbne1JNLIROAUxJ3sDq' in parents",
        fields="nextPageToken, files(id, name, mimeType, parents)",
        orderBy="modifiedByMeTime desc").execute()

    file_metadata = {'name': 'hello.py'}
    media = MediaFileUpload('hello.py')
    file = drive_service.files().create(body=file_metadata,
                                        media_body=media,
                                        fields='id').execute()
    print(file['id'])

    for item in results['files']:
        print(item)
    # 112V1rDMqEyWGeSbne1JNLIROAUxJ3sDq
    # subf - 1tNa9kp5eJqczAzs15m_hsQNH45MsVIhx
    # for item in items:
    #     print(type(item))


if __name__ == '__main__':
    main()
