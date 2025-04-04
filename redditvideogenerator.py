import praw
import os
import pyttsx3
import soundfile as sf
import random
import datetime as dt
from moviepy.editor import *
import configparser


""" Reddit Account, and PRAW API required """
""" ffmpeg can be downloaded from https://ffmpeg.org/download.html """
""" PRAW API can be setup by following https://praw.readthedocs.io/en/latest/getting_started/quick_start.html """
""" ffmpeg must be added to PATH in order for editrawfootage() function to work """
""" Change the exampleconfig.ini file to your liking and rename to config.ini """
""" Make sure your path to the config.ini is correct """
""" static video is stitched between each post and the outro video is at the end """
""" if you want to skip ffmpeg installation and use pre edited videos, comment out the editrawfootage() at line 204 """

configpath = "C:\\Users\\USERNAME\\downloads\\redditapp\\config.ini"

config = configparser.ConfigParser()
config.read(configpath)

static = VideoFileClip(config["DEFAULT"]["staticvideodirectory"])
outro = VideoFileClip(config["DEFAULT"]["outrodirectory"])

reddit = praw.Reddit(client_id=config["DEFAULT"]["clientid"],
                     client_secret=config["DEFAULT"]["clientsecret"],
                     user_agent=config["DEFAULT"]["useragent"])

def editrawfootage() -> None:
    print("Checking for any gameplay to add to background video directory...")
    rawfootage = os.listdir(config["DEFAULT"]["rawfootagedirectory"])
    if not rawfootage: # check if list is empty
        print("-- No raw footage found in the directory --")
    
    else:
        for file in rawfootage:
            try:
                os.system(f"ffmpeg -ss 00:01:00 -i {config["DEFAULT"]["rawfootagedirectory"]}{file} -c:v copy -c:a copy {config["DEFAULT"]["rawfootagedirectory"]}{file}")
                print("Deleted original...")
                os.remove(f"{config["DEFAULT"]["rawfootagedirectory"]}{file}")
                print(f"Processed {file} and moved to {config["DEFAULT"]["backgroundvideodirectory"]}")

            except Exception as e:
                print(f"Failed to process {file} with error: {e}")
                continue

def getusedposts():
    with open(config["DEFAULT"]["usedpostsdirectory"], "r") as f:
        usedposts = f.readlines()
    return usedposts

def saveusedposts(post_ids: list) -> None:
        with open(config["DEFAULT"]["usedpostsdirectory"], "a") as f:
            for post in post_ids:
                f.write(post+"\n")

def generatevoiceoverfile(text: str, title: str) -> tuple:
    engine = pyttsx3.init()                   
    voices = engine.getProperty('voices')
    rate = engine.getProperty('rate')
    engine.setProperty('rate', rate-45)
    engine.setProperty('voice', voices[2].id) 
    engine.save_to_file(text, f"{config["DEFAULT"]["voiceoverdirectory"]}voiceover{title}.mp3")
    engine.runAndWait()
    audio_file = sf.SoundFile(f"{config["DEFAULT"]["voiceoverdirectory"]}voiceover{title}.mp3")
    duration = len(audio_file) / audio_file.samplerate
    audio_file.close()

    return duration, f"{config["DEFAULT"]["voiceoverdirectory"]}voiceover{title}.mp3"

def gettopposts(subreddit: str, limit: int) -> list:
    print(f"Obtaining {limit} post ids from r/{subreddit}...")
    
    subreddit = reddit.subreddit(subreddit).top(time_filter="all", limit=int(limit))
    post_ids = []
    for s in subreddit: 
        # pprint.pprint(vars(s))
        submission = reddit.submission(id=s.id)
        post_ids.append(s.id)
        usedpost_ids = getusedposts()
        copypost_ids = post_ids
        for post in post_ids:
            if f"{post}\n" in usedpost_ids:
                copypost_ids.remove(post)

    return copypost_ids

def searchforposts(searchterm: str, subreddit: str) -> list:
    searchresults = list(reddit.subreddit(subreddit).search(searchterm))[:10]
    post_ids = []
    for s in searchresults: 
        # pprint.pprint(vars(s))
        post_ids.append(s.id)
        usedpost_ids = getusedposts()
        copypost_ids = post_ids
        for post in post_ids:
            if f"{post}\n" in usedpost_ids:
                copypost_ids.remove(post)  
 
    return copypost_ids

def getpostidbyurl(url: str) -> str:
    submission = reddit.submission(url=url)
    usedpostids = getusedposts()
    if submission.id in usedpostids:
        return None

    else:
        return submission.id

def gatherpostinfo(post_ids: list) -> list:
    post_info = []
    
    for post in post_ids:
        print(f"Gathering Data for Post ID: {post}...")
        commentlist = []
        submission = reddit.submission(id=post)
        submission.comments.replace_more(limit=0)

        for top_level_comment in submission.comments:
            commentlist.append(top_level_comment.body)

        if len(commentlist) == 0:
            post_info.append((submission.title, submission.author, submission.selftext, post, ""))
        else:
            post_info.append((submission.title, submission.author, submission.selftext, post, commentlist[0]))

    return post_info

def getbackgroundvideo(postaudiolength):
    # get a random video from the backgroundvideodir, then a random section of that video that matches the length of the audio
    files = os.listdir(config["DEFAULT"]["backgroundvideodirectory"])
    randomfile = random.choice(files)
    filepath = os.path.join(config["DEFAULT"]["backgroundvideodirectory"], randomfile)
    video = VideoFileClip(filepath).set_audio(0)
    randomstartingpoint = random.randint(100, int(video.duration-postaudiolength))
    subclip = video.subclip(randomstartingpoint, randomstartingpoint+postaudiolength)
    return subclip

def clearvoiceoverdir() -> None:
    files = os.listdir(config["DEFAULT"]["voiceoverdirectory"])
    try:
        for file in files:
            os.remove(os.path.join(config["DEFAULT"]["voiceoverdirectory"], file))

    except Exception as e:
        print(f"Error removing old voiceover files: {e}")


def generatecompletedvideo(subreddit: str, limit: int) -> None:
    print(f"---------- Generating video for r/{subreddit} ----------")
    clearvoiceoverdir()
    print(f"Cleared voiceover directory: {config["DEFAULT"]["voiceoverdirectory"]}")
    clips = []
    postids = gettopposts(subreddit, limit)
    postinfo = gatherpostinfo(postids) # list of tuples with post info

    print(f"Posts gathered for {subreddit}: {postids}")

    for post in postinfo:

        """
        post[0] = post title
        post[1] = post author
        post[2] = post text
        post[3] = post id
        post[4] = top comment
        """

        if len(post[4]) > 0:
            postaudiolength = generatevoiceoverfile(f"{post[0]} by {post[1]}. {post[2]}. {post[4]}", f"-{post[3]}-{dt.datetime.now().isoformat()[:10]}")[0]
            postaudiopath = generatevoiceoverfile(f"{post[0]} by {post[1]}. {post[2]}. {post[4]}", f"-{post[3]}-{dt.datetime.now().isoformat()[:10]}")[1]

        else:
            postaudiolength = generatevoiceoverfile(f"{post[0]} by {post[1]}. {post[2]}.", f"-{post[3]}-{dt.datetime.now().isoformat()[:10]}")[0]
            postaudiopath = generatevoiceoverfile(f"{post[0]} by {post[1]}. {post[2]}.", f"-{post[3]}-{dt.datetime.now().isoformat()[:10]}")[1]

        with open(f"{config["DEFAULT"]["scriptdirectory"]}{subreddit}-{dt.datetime.now().isoformat()[:10]}-script.txt", "a") as f:
            f.write(f"{post[0]} by {post[1]}. {post[2]}. {post[4]}\n-----------------------------------------------------------------------------------------------------------------------------\n")
            f.close()

        print(f"Script file updated: {config["DEFAULT"]["scriptdirectory"]}-{subreddit}-{dt.datetime.now().isoformat()[:10]}-script.txt")
        print(postaudiopath)
        
        postaudio = AudioFileClip(postaudiopath).set_duration(postaudiolength)
        print(f"Audio length for Post id {post[3]}: {int(postaudiolength)} seconds\n--------------------------------------------------------------------------------------------------------------------------\n")
        backgroundvideo = getbackgroundvideo(postaudiolength)
        video = backgroundvideo.set_audio(postaudio)
        clips.append(video)
        clips.append(static)
    
    clips.pop(-1) # remove last static clip
    
    clips.append(outro) # add outro clip
    clips.append(static)
    print(clips)
    concatenate_videoclips(clips, method="compose").write_videofile(f"{config["DEFAULT"]["finishedvideodirectory"]}{subreddit}{dt.datetime.now().isoformat()[:10]}.mp4", fps=30, codec="libx264")
    print(f"Finished video for {subreddit}\n----------------------------------------------------------------\n")
    saveusedposts(postids)
    
def main() -> None:
    editrawfootage() # edit and move any raw gameplay footage to background video directory
    poststogather = ["nuclearrevenge", "prorevenge", "TalesFromTheFrontDesk", "talesfromtechsupport", "talesfromretail", "talesfromcallcenters", "talesfromthejob", "pettyrevenge", "AITAH"]
    for subreddit in poststogather:
        try:
            generatecompletedvideo(subreddit, 7)

        except Exception as e:
            print(f"Error generating video for {subreddit}: {e}")
            continue

if __name__ == "__main__":
    main()