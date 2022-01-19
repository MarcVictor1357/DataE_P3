from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.engine import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import MetaData
from sqlalchemy import Table, Column, Integer, String, Float
import pandas as pd
import time
import os

# creating a FastAPI server
request_server = FastAPI(title='User API for Lyrics database')

# creating a connection to the database
mysql_url = 'localhost:3306'
mysql_user = 'root'
#mysql_password = 'ziggy'   # os.environ.get('LEPASSWORD')
database_name = 'LyricsDb'   # Le nom de la bdd créée via le docker-compose

# recreating the URL connection
#connection_url = 'mysql://{user}:{password}@{url}/{database}'.format(
connection_url = 'mysql://{user}@{url}/{database}'.format(
    user=mysql_user,
    #password=mysql_password,
    url=mysql_url,
    database=database_name
)

# Create the connection
try:
    my_engine = create_engine(connection_url)
except SQLAlchemyError as cre_e1:
    print("SQL alchemy error:")
    print(cre_e1)
print("Engin de connection créé.")

# Connect to database engine:
# Several attempts until database server is running:
created = 0
for x in range(10):
    if (created==-1):
        time.sleep(5)
    elif (created==1):
        print("Connection au SGBD effectuée.")
        break
    try:
        conn = my_engine.connect()
    except SQLAlchemyError as con_e1:
        print("SQL alchemy error on attempt nb."+str(x)+":")
        print(con_e1)
        created = -1
        pass   #continue
    else:
        created = 1

# Unuseful because this db was created via docker-compose:
#try:
#    conn.execute("CREATE DATABASE IF NOT EXISTS LyricsDb")
#except SQLAlchemyError as credb_e1:
#    print("SQL alchemy error:")
#    print(credb_e1)
#print("Database created.")

# Create tables:
meta = MetaData()
artistes = Table(
    'Artists', meta,
    Column('Artist', String(256), primary_key=True),
    Column('Songs', Integer),   # Number of songs
    Column('Popularity', Float),
    Column('Link', String(256)),   # Link to the artist's page
    Column('Genre', String(256)),   # Primary musical genre
    Column('Genres', String(256)),
    extend_existing=True   #si elle existe déjà, ça ne le pertube pas, il redéfinira les options et colonnes sur cette table existante
    )
paroles = Table(
    'Lyrics', meta,
    Column('ALink', String(256)),   # Link to artist's page
    Column('SName', String(256)),   # Song name
    Column('SLink', String(512), primary_key=True),   # Link to lyric's page
    Column('Lyric', String(5000)),   # Lyrics
    Column('Idiom', String(64)),   # Language
    extend_existing=True   #si elle existe déjà, ça ne le pertube pas, il redéfinira les options et colonnes sur cette table existante
    )
meta.create_all(my_engine)
print("Table Artists créée.")
print("Table Lyrics créée.")
print("Liste des tables :")
print(meta.tables.keys())


# Load artists data via pandas dataframe:
df = pd.read_csv("artists-data.csv",sep=',',quotechar='"',encoding='utf8')
# Truncate too long strings:
df['Artist'] = df['Artist'].str.slice(0,255)
df['Link'] = df['Link'].str.slice(0,255)
df['Genre'] = df['Genre'].str.slice(0,255)
df['Genres'] = df['Genres'].str.slice(0,255)
# Drop duplicates:
df.drop_duplicates(subset=['Artist'],inplace=True)
# Load into DB table:
df.to_sql('Artists',con=my_engine,index=False,if_exists='append')
print("Données des artistes chargées.")

# Load lyrics data via pandas dataframe:
df = pd.read_csv("lyrics-data.csv",sep=',',quotechar='"',encoding='utf8')
# Truncate too long strings:
df['ALink'] = df['ALink'].str.slice(0,255)
df['SName'] = df['SName'].str.slice(0,255)
df['SLink'] = df['SLink'].str.slice(0,511)
df['Lyric'] = df['Lyric'].str.slice(0,4999)
df['Idiom'] = df['Idiom'].str.slice(0,63)
# Drop duplicates:
df.drop_duplicates(subset=['SLink'],inplace=True)
# Load into DB table:
df.to_sql('Lyrics',con=my_engine,index=False,if_exists='append')
print("Données des paroles chargées.")

# Create an Artist class
class Art(BaseModel):
    name: str = ''
    nbsongs: int = 0
    popularity: float = 0.0
    link: str = ''
    genre: str = ''
    genres: str = ''
# Create a Song class
class Song(BaseModel):
    alink: str = ''
    sname: str = ''
    slink: str = ''
    lyric: str = ''
    idiom: str = ''



@request_server.get('/status')
async def get_status():
    """Returns 1
    """
    return 1



@request_server.get('/artist/{partofname:str}')
async def get_searchartist(partofname):
    """Returns description of all artists with that string (parameter) inside their names
    """
    results = conn.execute("SELECT * FROM Artists WHERE (Artists.Artist LIKE '%%{}%%');".format(partofname))
    resultats = [
        Art(
            name=i[0],
            nbsongs=i[1],
            popularity=i[2],
            link=i[3],
            genre=i[4],
            genres=i[5]
            ) for i in results.fetchall()]
    lesnoms = [o.name for o in resultats]
    return lesnoms



@request_server.get('/popu/{popu:float}')
async def get_artistspopu(popu):
    """Returns list of artists whose popularity is >= that number (parameter)
    """
    results = conn.execute("SELECT * FROM Artists WHERE (Artists.Popularity >= {});".format(str(popu)))
    class Artpop(BaseModel):
        name: str = ''
        #nbsongs: int = 0
        popularity: float = 0.0
        #link: str = ''
        #genre: str = ''
        #genres: str = ''
    resultats = [
        Artpop(
            name=i[0],
            #nbsongs=i[1],
            popularity=i[2]   #,
            #link=i[3],
            #genre=i[4],
            #genres=i[5]
            ) for i in results.fetchall()]
    return resultats



@request_server.get('/genrelist')   # Liste des genres de musique
async def get_genrelist():
    """Returns list of all existing primary music genres in the database (no parameter)
    """
    results = conn.execute("SELECT Genre FROM Artists GROUP BY Genre;")
    class Artgenre(BaseModel):
        genre: str = ''
    resultats = [
        Artgenre(
            genre=i[0]
            ) for i in results.fetchall()]
    return resultats



@request_server.get('/genre/{genre:str}')
async def get_artistsgenre(genre):
    """Returns list of artists with that primary music genre (parameter)
    """
    results = conn.execute("SELECT * FROM Artists WHERE (Artists.Genre LIKE '%%{}%%');".format(genre))
    class Artpop(BaseModel):
        name: str = ''
        #nbsongs: int = 0
        #popularity: float = 0.0
        #link: str = ''
        genre: str = ''
        #genres: str = ''
    resultats = [
        Artpop(
            name=i[0],
            #nbsongs=i[1],
            #popularity=i[2],
            #link=i[3],
            genre=i[4]   #,
            #genres=i[5]
            ) for i in results.fetchall()]
    return resultats



@request_server.get('/songs/{artist:str}')   # Liste des chansons de l'artiste
async def get_songs(artist):
    """Returns list of songs from the artist (parameter)
    """
    results = conn.execute("SELECT Artists.Artist,Lyrics.SName FROM Artists INNER JOIN Lyrics ON (Artists.Link=Lyrics.ALink) WHERE (Artists.Artist LIKE '%%{}%%');".format(artist))
    class Res(BaseModel):
        artist: str = ''
        song: str = ''
    resultats = [
        Res(
            artist=i[0],
            song=i[1]
           ) for i in results.fetchall()]
    return resultats



@request_server.get('/songartword/{artistandword}')   # Liste des chansons de l'artiste, avec une partie du nom de chanson
async def get_songartword(artist:str,word:str):
    """Returns list of songs from the artist (parameter artist), with a title containing that string (parameter word)
    """
    results = conn.execute("SELECT Artists.Artist,Lyrics.SName FROM Artists INNER JOIN Lyrics ON (Artists.Link=Lyrics.ALink) WHERE (Artists.Artist LIKE '%%{}%%' AND Lyrics.SName LIKE '%%{}%%');".format(artist,word))
    class Res(BaseModel):
        artist: str = ''
        song: str = ''
    resultats = [
        Res(
            artist=i[0],
            song=i[1]
           ) for i in results.fetchall()]
    return resultats



@request_server.get('/lyrics/{artistandword}')   # Paroles d'une chanson de l'artiste, avec une partie du nom de chanson
async def get_lyrics(artist:str,word:str):
    """Returns lyrics of a song from the artist (parameter artist), with a title containing that string (parameter word). This will work only if there is a unique song. The user can select accurately thanks to the songartword endpoint.
    """
    results = conn.execute("SELECT Artists.Artist,Lyrics.SName,Lyrics.Lyric FROM Artists INNER JOIN Lyrics ON (Artists.Link=Lyrics.ALink) WHERE (Artists.Artist LIKE '%%{}%%' AND Lyrics.SName LIKE '%%{}%%');".format(artist,word))
    class Res(BaseModel):
        artist: str = ''
        song: str = ''
        lyric: str = ''
    resultats = [
        Res(
            artist=i[0],
            song=i[1],
            lyric=i[2]
           ) for i in results.fetchall()]
    if len(resultats) == 0:
        return "No song matches the parameters."
    elif len(resultats) == 1:
        return resultats
    else:
        return "More than 1 song match. Please enter more accurate parameters."



@request_server.get('/fulltext/{word:str}')   # Liste des chansons contenant une chaine de caractères dans leurs paroles
async def get_fulltext(word:str):
    """Returns the list of songs in which this string (parameter) appears.
    """
    results = conn.execute("SELECT Artists.Artist,Lyrics.SName,Lyrics.Lyric FROM Artists INNER JOIN Lyrics ON (Artists.Link=Lyrics.ALink) WHERE (Lyrics.Lyric LIKE '%%{}%%');".format(word))
    class Res(BaseModel):
        artist: str = ''
        song: str = ''
        lyric_extract: str = ''
    resultats = [
        Res(
            artist=i[0],
            song=i[1],
            lyric_extract=i[2]
           ) for i in results.fetchall()]
    if len(resultats) == 0:
        return "No song contains that string."
    else:
        for i in range(len(resultats)):
            index_start_word = ((resultats[i].lyric_extract).upper()).find(word.upper())
            index_end_word = index_start_word+len(word)-1
            index_start = max(index_start_word-40,0)
            index_end = min(index_end_word+40,len(resultats[i].lyric_extract)-1)
            nb_pads_before = min(index_start,25)
            nb_pads_after = min(len(resultats[i].lyric_extract)-1-index_end,25)
            resultats[i].lyric_extract = ("."*nb_pads_before) + (resultats[i].lyric_extract)[index_start:index_end+1] + ("."*nb_pads_after)
        return resultats


