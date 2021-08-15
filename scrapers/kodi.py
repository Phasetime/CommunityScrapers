import os
import sys
import json
import sqlite3
import mimetypes
import base64
import xml.etree.ElementTree as ET
"""  
This script parses kodi nfo files for metadata. The .nfo file must be in the same directory as the video file and must be named exactly alike.
"""

# If you want to ingest image data from the nfo you may need to rewrite the path stored in the file. Especially when using a docker container.
rewriteBasePath = True
basePathBefore = 'Z:'
basePathAfter = "/data"

def query_xml(path, title):
    tree=ET.parse(path)
    # print(tree.find("title").text, file=sys.stderr)
    if title == tree.find("title").text:
        debug("Exact match found for " + title)
    else:
        debug("No exact match found for " + title + ". Matching with " + tree.find("title").text + "!")
    
    # Extract matadata from xml
    res={"title":title}
    if tree.find("title") != None:
        res["title"] = tree.find("title").text
    if tree.find("plot") != None:
        res["details"] = tree.find("plot").text
    if tree.find("releasedate") != None:
        res["date"] = tree.find("releasedate").text
    if tree.find("tag") != None:
        res["tags"]=[{"name":x.text} for x in tree.findall("tag")]
    if tree.find("genre") != None:
        if res["tags"] is not None:
            res["tags"] += [{"name":x.text} for x in tree.findall("genre")]
        else:
            res["tags"] = [{"name":x.text} for x in tree.findall("genre")]
    if tree.find("actor") != None:
        res["performers"] = []
        for actor in tree.findall("actor"):
            if actor.find("type").text == "Actor":
                res["performers"].append({"name": actor.find("name").text})
    if tree.find("studio") != None:
        res["studio"] = {"name":tree.find("studio").text}
    
    posterElem = tree.find("art").find("poster")
    if posterElem.text != None:
        if not rewriteBasePath and os.path.isfile(posterElem.text):
            res["image"] = make_image_data_url(posterElem.text)
        elif rewriteBasePath:
            rewrittenPath = posterElem.text.replace(basePathBefore, basePathAfter).replace("\\", "/")
            if os.path.isfile(rewrittenPath):
                res["image"] = make_image_data_url(rewrittenPath)
            else:
                debug("Can't find image: " + posterElem.text.replace(basePathBefore, basePathAfter) + ". Is the base path correct?")
        else:
            debug("Can't find image: " + posterElem.text + ". Are you using a docker container? Maybe you need to change the base path in the script file.")

    return res

def debug(s):
    print(s, file=sys.stderr)

# Would be nicer with Stash API instead of direct SQlite access
def get_file_path(scene_id):
    db_file = "../stash-go.sqlite"

    con = sqlite3.connect(db_file)
    cur = con.cursor()
    for row in cur.execute("SELECT * FROM scenes where id = " + str(scene_id) + ";"):
        #debug_print(row)
        filepath = row[1]
    con.close()
    return filepath
    
def make_image_data_url(image_path):
    # type: (str,) -> str
    mime, _ = mimetypes.guess_type(image_path)
    with open(image_path, 'rb') as img:
        encoded = base64.b64encode(img.read()).decode()
    return 'data:{0};base64,{1}'.format(mime, encoded)
        
if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    
    # Assume that .nfo is named exactly like the video file and is at the same location
    # WORKAROUND: Read file name from db until filename is given in the fragment
    videoFilePath = get_file_path(fragment["id"])
    
    # Reconstruct file name for .nfo
    temp = videoFilePath.split(".")
    temp[-1] = "nfo"
    nfoFilePath = ".".join(temp)
    
    if os.path.isfile(nfoFilePath):
        res = query_xml(nfoFilePath, fragment["title"])
        debug(res)
        print(json.dumps(res))
    else:
        debug("No file found at" + nfoFilePath)
        
    exit(0)