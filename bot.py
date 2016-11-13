import traceback
import praw
import time
import sqlite3
import PIL
from PIL import Image
from PIL import ImageEnhance
import requests
import io
from io import BytesIO
from inspect import currentframe, getframeinfo
import re
import uuid
import dropbox
import datetime


#Code partly stolen from https://github.com/voussoir/reddit/blob/master/ReplyBot/replybot.py

'''USER CONFIGURATION'''

APP_ID = "geIk69_GPRGxDA"
APP_SECRET = "penis haha"
APP_URI = "https://127.0.0.1:65010/authorize_callback"
APP_REFRESH = 'penis haha'
USERAGENT = "u/Okimoka image editor"
SUBREDDIT = "me_irl"
# This is the sub or list of subs to scan for new posts. For a single sub, use "sub1". For multiple subreddits, use "sub1+sub2+sub3+..."
COMMANDS = ["crop","saturate"]
# These are the words you are looking for
MAXPOSTS = 100
# This is how many posts you want to retrieve all at once. PRAW can download 100 at a time.
WAIT = 30
# This is how many seconds you will wait between cycles. The bot is completely inactive during this time.



try:
    import bot
    USERAGENT = bot.aG
except ImportError:
    pass

print('Opening SQL Database')
sql = sqlite3.connect('sql.db')
cur = sql.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS oldimages(id TEXT)')
cur.execute('CREATE INDEX IF NOT EXISTS oldimage_index ON oldimages(id)')




print('Logging in...')
r = praw.Reddit(USERAGENT)
r.set_oauth_app_info(APP_ID, APP_SECRET, APP_URI)
r.refresh_access_information(APP_REFRESH)

dbx = dropbox.Dropbox('penis haha')
dbx.users_get_current_account()
#print(dir(dbx))

def replyComment(message, to, isCommentDone):
    attachment = " ^^[contact/feedback](https://www.reddit.com/message/compose/?to=Okimoka)"
    try:
        to.reply(message + attachment)
        print("Replied to " + to.id + " with: " + message)
        if isCommentDone:
            cur.execute('INSERT INTO oldimages VALUES(?)', [to.id])
            sql.commit()
    except:
        print('Replying to the comment failed')



def scanbot():

    print('Searching %s.' % SUBREDDIT)
    subreddit = r.get_subreddit(SUBREDDIT)
    comments = []
    comments += list(subreddit.get_comments(limit=MAXPOSTS))
    comments.sort(key=lambda x: x.created_utc)

    for comment in comments:


        try:
            pauthor = comment.author.name
        except AttributeError:
            # Author is deleted. Skip comment
            continue

        pbody = comment.body.lower()

        if "/u/imageeditbot" not in pbody:
            # This comment doesn't mention the bot. Skip comment
            continue

        cur.execute('SELECT * FROM oldimages WHERE ID=?', [comment.id])
        if cur.fetchone():
            print("Post already in database")
            continue

        m = re.search("\/u\/imageeditbot ([^\s]+) ([^\s]+)",pbody)
        #m.group 0: Entire comment
        #m.group 1: command
        #m.group 2: parameter



        if m.group(1) not in COMMANDS:
            replyComment("Invalid command \"%s\"" % m.group(1), comment, 1)
            continue



        ##### CHECKING FOR VALID PARAMETERS #####

        if m.group(1) == "crop":
            try:
                nums = re.findall("\d+", m.group(2))
                proportionDesired = [float(nums[0]),float(nums[1])]
                if 0 in proportionDesired:
                    replyComment("No", comment, 1)
                    continue
            except:
                replyComment("Invalid proportion parameter, Syntax: X:Y", comment, 1)
                continue


        if m.group(1) == "saturate":
            try:
                int(m.group(2))
            except:
                replyComment("Invalid parameter (expected single signed integer)", comment, 1)
                continue

        ##### END PARAMETER CHECKING #####



        pid = comment.id


        cur.execute('INSERT INTO oldimages VALUES(?)', [pid])
        sql.commit()


        print("DOING POST ID ", pid)
        purl = comment.submission.url
        if "/imgur.com/" in purl or ".gyazo.com/" in purl or ".reddituploads.com/" in purl:
            if not(purl.endswith(".jpg")) and not(purl.endswith(".png")):
                purl = purl + ".png"
        if purl.endswith(".jpg") or purl.endswith(".png"):
            print('Post URL: %s . Making a request now' % purl)
            response = requests.get(purl)
            try:


                if m.group(1) == "crop":
                    print("Cropping Image")
                    img = Image.open(BytesIO(response.content))
                    w, h = img.size
                    wSteps = w/proportionDesired[0]
                    hSteps = h/proportionDesired[1]
                    print("IMAGE COMING UP")
                    if wSteps < hSteps:
                        heightDiff = h-proportionDesired[1]*wSteps
                        img = img.crop((0,heightDiff/2,w,h-heightDiff/2))
                    if wSteps > hSteps:
                        widthDiff = w-proportionDesired[0]*hSteps
                        img = img.crop((widthDiff/2,0,w-widthDiff/2,h))
                    print("IMAGE CROPPED")
                    output = io.BytesIO()
                    img.save(output, format='PNG')


                if m.group(1) == "saturate":
                    print("Saturating Image")
                    img = Image.open(BytesIO(response.content))
                    w, h = img.size
                    n = int(m.group(2))
                    H = 0
                    if n<0:
                        H=1-n/100
                        if H<0:
                            H=0
                    else:
                        H=1+n/100
                    converter = PIL.ImageEnhance.Color(img)
                    img2 = converter.enhance(H)
                    output = io.BytesIO()
                    img2.save(output, format='PNG')


                print(m.group(1))



                print("IMAGE EDITED")
                randdate = datetime.datetime.now().strftime("%y%m%d%H%M%f")
                dbx.files_upload(output.getvalue(), '/test_dropbox/IMG%s.png' % randdate)
                print("IMAGE UPLOADED")
                replyComment("[Here](https://www.dropbox.com/sh/v5qm7x9o5n0n402/AABEoxy9sej5SgDgx_wGApe0a?dl=0&preview=IMG"+randdate+".png) is your edited image!", comment, 0)

            except Exception as exce:
                print('Error: ' + exce)
                #continue
        else:
            replyComment("Post is not a direct image link. Sorry", comment, 1)
        

        print("REACHED END OF LOOP")


while True:
    scanbot()
    print('Running again in %d seconds \n' % WAIT)
    time.sleep(WAIT)
