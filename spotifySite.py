from flask import Flask, redirect, session, request, render_template, jsonify
import urllib.parse, requests, base64, os
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key= 'YNT03OihVBbA5Lo12kewx8KMzDjTVwim'

REDIRECT_URI = 'http://127.0.0.1:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

scope = 'playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public'

#function for if token expired (return types: boolean vs funtion)
def accessTokenCheck():
    if 'access_token' not in session:
        return redirect('/login')
    else:
        if datetime.now().timestamp() > session['expires_at']: # expireeeed
            print("token expired")
            return redirect('/refreshToken')
            
def querySpotify(endpoint):
    if type(endpoint) == str:
        accessTokenCheck()
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

def makeTextFile(tracks, playlistName):
    f = open(f"{playlistName}.txt", 'w')
    
    f.write("Format: Song, album - artists \n\n")
    
    for track in tracks:
        name = track['track']['name']
        album = track['track']['album']['name']
        
        #TODO get all artist + features
        artists = track['track']['artists']
        artistNames = ''
        for artist in artists:
            if artist['type'] == 'artist':
                artistNames = artist['name'] + ', '
        
        f.write(f'{name}, {album} - {artistNames}\n')
        #print(track)
    
    f.close()
    return f

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
        #'show_dialog': True
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
            'client_id': getClientID(),
            'client_secret': getClientSecret()
        }

        response = requests.post(TOKEN_URL, data=req_body)
        newTokenInfo = response.json()
        session['access_token'] = newTokenInfo['access_token']
        session['expires_at'] = datetime.now().timestamp() + newTokenInfo['expires_in']

        return redirect('/home')

'''
--------------LOGGED PAGES--------------
'''

@app.route('/home')
def home():
    response = querySpotify('me')
    userInfo = response.json()
   #if userInfo['type'] == "user"

    session['user_display_name'] = userInfo['display_name']
    session['user_id'] =  userInfo['id']
    session['images'] = userInfo['images']

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

#check if sing has tracks
#TODO (MAke downlaodable) SEND HTML <Path>
    #https://linkdoctor.io/create-download-link/
@app.route('/playlistToText/<id>')
def playlistToText(id): 
    print('getting playlist info')
    response = querySpotify(f'playlists/{id}')
    
    playlistInfo = response.json()
    images = playlistInfo['images'] #TODO
    tracks = playlistInfo['tracks']['items'] #list
    
    #print(type(tracks))

    nextPage = playlistInfo['tracks']['next'] 

    #print('Next page type: ', type(nextPage))

    try:
        morePlaylistInfo = requests.get(nextPage, headers={
            'Authorization': 'Bearer '+ session['access_token']
        }).json()
    except:
        fileOutput = makeTextFile(tracks, playlistInfo['name'])
        print('Tracks size: ', len(tracks))

        return render_template('toText.html', tracks=tracks, playlistInfo=playlistInfo, file=fileOutput)
        

    #?proper nextPage check(weed out nextPage = None) || check by # songs vs sizeof tracks
    while nextPage: #USE tracks size
        #open next page
        #print('Page to visit : ', nextPage)
        #TODO CLEAN UP
        try:
            morePlaylistInfo = requests.get(nextPage, headers={
                'Authorization': 'Bearer '+ session['access_token']
            }).json()
        except:
            break

        moreTracks = morePlaylistInfo['items']
        #add to tracks ?track data type?
        tracks.extend(moreTracks)
        #set nextpage
        nextPage = morePlaylistInfo['next']
        #print('going to: ', nextPage)

    print('making text file')
    fileOutput = makeTextFile(tracks, playlistInfo['name'])

    print('Tracks size: ', len(tracks))
    
    #return str(tracks)
    return render_template('toText.html', tracks=tracks, playlistInfo=playlistInfo, file=fileOutput)

#scope: playlist-modify-public playlist-modify-private
#TODO list  !!Make Chrome Extention!!
    #!!!Make spoitfy Search Bar!!! (? get data in python and handle file in JS || JS read .env + reauth || )
    #Make spotify playlist || check playlist exstis (? allow user to pick name)
    #Add songs to playlist

    #? create/find ToListenTo app
    # search -> reusults(has serach + has add to playlist)

def search(query, type):
    accessTokenCheck()
    headers ={
        'Authorization': 'Bearer '+ session['access_token']
    }
    if type:
        response = requests.get(f"{API_BASE_URL}search?q={query}&type={type}", headers=headers)
    else:
        response = requests.get(f"{API_BASE_URL}search?q={query}", headers=headers)
    return response

#TODO finish
def addToSpotfyPlaylist(songUri, playlistID):
    accessTokenCheck()
    print([songUri])
    body = {
        "uris": [songUri],
        "position": 0
    }
    headers ={
        'Authorization': 'Bearer '+ session['access_token']
    }

    url = f"{API_BASE_URL}playlists/{playlistID}/tracks?uris={songUri}"
    
    response = requests.post(url, headers=headers)
    
    return response 

#TODO FIX
def createPlaylist(playlistName, playlistDescrip):
    url = f"{API_BASE_URL}users/{session['user_id']}/playlists"
    body = {
        "name": playlistName,
        "description": playlistDescrip,
        "public": "false"
    }
    headers = {'Authorization': 'Bearer '+ session['access_token'],
               'Content-Type': 'application/json'
               }
    
    response = requests.post(url,data=body,headers=headers)
    
    return response

#TODO make custom playlist
@app.route('/toListenTo', methods=["GET", "POST"])
def toListenTo():
    if request.method == 'POST':
        if request.form['PlaylistSelected'] == 'Custom':
            #create PLaylist
            response = createPlaylist("Test_Spotify Site","This is a test")
            #id = response.json()['id']
            return response.json()
        else:
            print("Playlist: " , request.form['PlaylistSelected'] )
            print(request.form['PlaylistSelected'].split(','))
            session['playlistToAddTo_name'] = request.form['PlaylistSelected'].split(',')[0][2:-1]
            session['playlistToAddTo_ID'] = request.form['PlaylistSelected'].split(',')[1][2:-2]
            print('storing in session:', request.form['PlaylistSelected'].split(',')[1][2:-2])
        #todo add images

    
    return render_template('toListenTo.html')

@app.route('/search', methods=['POST'])
def searched():
     if request.method == 'POST':
         #print(request.view_args)
         
         #TODO fix song type recognition
         if request.form['searchbar']:
            response = search(request.form['searchbar'], 'track') #fix song type recognition
            #return response.json()['tracks']['items']
            
            results = response.json()['tracks']['items']
            href = response.json()['tracks']['href']
            for x in results:
                x['album'].pop('available_markets')
                
            #return str(results)
            return render_template('search.html', results=results)
                   
     #response = search(searcehdStr)
     return redirect('/toListenTo')

#TODO add to playlist 
@app.route('/addToPlaylist', methods=['POST'])
def addToPlaylist():
    if request.method == 'POST':
        item = request.form['itemToAdd']
        print('songURI: ', item)
        print('playlistID: ', session['playlistToAddTo_ID'])
        response = addToSpotfyPlaylist(item, session['playlistToAddTo_ID'])
        print(response)
    return ";)"

#TODO scroll playlists
@app.route('/select_PlaylistToAddTo')
def select_PlaylistToAddTo():
    response = querySpotify('me/playlists')
    playlistInfo = response.json()

    href = playlistInfo['href']
    
    remaning = f"{playlistInfo['offset']} - {playlistInfo['limit'] + playlistInfo['offset']} of {playlistInfo['total']} "

    playlists = playlistInfo['items']
    #return str(playlists)
    return render_template('select_PlaylistToAddTo.html', playlists=playlists, remaining = remaning)




 
#scope: 
@app.route('/spotifyStats')
def spotifyStats():
    return "spotifyStats Comming Soon!!!"


if __name__ == "__main__":
    app.run(debug=True)