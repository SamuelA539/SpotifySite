from flask import Flask, redirect, session, request, render_template, jsonify
import urllib.parse, requests, base64, os
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key= 'YNT03OihVBbA5Lo12kewx8KMzDjTVwim'

# CLIENT_ID = 'faa8b2a6844c4219bc4d0954e84d0f29'
# CLIENT_SECRET = '5598ceb822d64670a11ec9c9d1b937f6'


REDIRECT_URI = 'http://127.0.0.1:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

scope = 'playlist-read-private playlist-read-collaborative'

#function for if token expired (return types: boolean vs funtion)
def accessTokenCheck():
    if 'access_token' not in session:
        return redirect('/login')
    else:
        if datetime.now().timestamp() > session['expires_at']: # expireeeed
            return redirect('/refreshToken')
            
def querySpotify(endpoint):
    if type(endpoint) == str:
        accessTokenCheck
        headers ={
            'Authorization': 'Bearer '+ session['access_token']
        }
        response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers)
        return response

def getClientID():
    load_dotenv()
    return os.getenv('client_id')

def getClientSecret():
    load_dotenv()
    return os.getenv('client_secret')

#TODO make pretty
@app.route('/')
def index():
    return render_template('welcome.html')

@app.route('/login')
def login():
    params = {
        'response_type': 'code',
        'client_id': getClientID(),
        'scope': scope,
        'redirect_uri':REDIRECT_URI,
        'show_dialog': True
     }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)

#TODO test codes
@app.route('/callback')
def callback():
    #return request
    if 'error' in request.args:
        # print('error found')
        return jsonify({"error": request.args['error']})
    
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,         
        } 

        idSecret = getClientID()+":"+getClientSecret()
        bytesS = idSecret.encode("utf-8")
        auth_base64 = str(base64.b64encode(bytesS), "utf-8")

        req_header = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': "Basic "+ auth_base64
        }
        
        response = requests.post(TOKEN_URL, data=req_body, headers=req_header)
        token_info = response.json()
        print('Token Info:', token_info)
        # return jsonify(token_info)

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        print(datetime.now())
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
        return redirect('/home')
    
#TODO test refreshing
@app.route('/refreshToken')
def refreshToken():
    if 'refresh_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        newTokenInfo = response.json()
        session['access_token'] = newTokenInfo['access_token']
        session['expires_at'] = datetime.now().timestamp() + newTokenInfo['expires_in']

        return redirect('/home')


#Logged Pages

@app.route('/home')
def home():
    response = querySpotify('me')
    userInfo = response.json()
   
    session['user_display_name'] = userInfo['display_name']
    session['user_id'] =  userInfo['id']

    images = userInfo['images']
    
    return render_template('home.html')

#scopes: playlist-read-private playlist-read-collaborative
#LOADING PLAYLISTS ISSUES
@app.route('/playlists')
def playlists():
    response = querySpotify('me/playlists')
    playlistInfo = response.json()

    href = playlistInfo['href']
    total = playlistInfo['total']
    playlists = playlistInfo['items'] #id: ['id'], name: ['name'], ownerName: ['owner']['display_name'], numTracks: ['tracks']['total'], type: ['type']

    return render_template('playlists.html', playlists=playlists, total=total)

@app.route('/playlistToText/<string:id>')
def playlistToText(id):
    response = querySpotify(f'playlists/{id}')
    
    playlistInfo = response.json()
    images = playlistInfo['images']
    tracks = playlistInfo['tracks']
    
    playlistInfo.pop('tracks')
    playlistInfo.pop('images')

    return render_template('toText.html', tracks=tracks, playlistInfo=playlistInfo)
    #return jsonify(tracks)

#scope: playlist-modify-public playlist-modify-private
@app.route('/toListenTo')
def toListenTo():
    return "To Listen To Comming Soon!!!"

#scope: 
@app.route('/spotifyStats')
def spotifyStats():
    return "spotifyStats Comming Soon!!!"


if __name__ == "__main__":
    app.run(debug=True)