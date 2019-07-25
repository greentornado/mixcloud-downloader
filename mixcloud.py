#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import urllib.parse
import re
from xml.dom import minidom
import datetime
import sys
from tqdm import tqdm
from bs4 import BeautifulSoup
import json
import requests

def download(mixurl):
    print("Trying to find manifest.mpd...")

    soup = BeautifulSoup(requests.get(mixurl).text, "html.parser")
    title = soup.title.string.replace("/","").replace("  "," ").replace("|","") + ".mp4"
    text = str(soup)

    trackid = re.search(r'((.\/){4}([^\/]*))\.mp3', text).group(1)

    mpdurl = "https://audio6.mixcloud.com/secure/dash2/" + trackid + ".m4a/manifest.mpd"
    print(mpdurl)

    text = requests.get(mpdurl).text

    dom = minidom.parseString(text)
    segtemplate = dom.getElementsByTagName('SegmentTemplate')
    initalization = segtemplate[0].attributes['initialization'].value
    media = segtemplate[0].attributes['media'].value
    segtimeline = dom.getElementsByTagName('S')
    fragcount = segtimeline[0].attributes['r'].value

    initalization = initalization.replace("$RepresentationID$", "a1-x3")
    media = media.replace("$RepresentationID$", "a1-x3")

    print("Downloading fragments...")

    data = requests.get(initalization).content

    start = datetime.datetime.now()

    for i in tqdm(range(1,int(fragcount) + 1)):
        data = data + requests.get(media.replace("$Number$",str(i))).content

    end = datetime.datetime.now()
    delta = end-start
    print("Downloaded and merged fragments in " + str(delta))

    file = open(title,"wb") 
    file.write(data)
    file.close()

def getMultiple(url):
    resp = requests.get(url)

    # First few tracks can be parsed from HTML
    soup = BeautifulSoup(resp.text, "html.parser")
    ahrefs = soup.find_all('a', {'class':"album-art",'href': True})
    hrefs = []
    for a in ahrefs:
        hrefs.append(a.get('href'))

    # Others have to be requested via Graphql
    gurl = "https://www.mixcloud.com/graphql"
    
    userid = re.search(r'userLookup&quot;:{&quot;id&quot;:&quot;(.*?==)',str(soup)).group(1)

    data = {"id":"q83","query":"query UserUploadsPageQuery($first_0:Int!,$lighten_2:Int!,$orderBy_1:CloudcastOrderByEnum!,$alpha_3:Float!) {_user1t8cpv:user(id:\""+ userid +"\") {id,...Fh}} fragment F0 on Picture {urlRoot,primaryColor} fragment F1 on User {id} fragment F2 on User {username,hasProFeatures,hasPremiumFeatures,isStaff,isSelect,id} fragment F3 on Cloudcast {isExclusive,isExclusivePreviewOnly,slug,id,owner {username,id}} fragment F4 on CloudcastTag {tag {name,slug,isCategory,id},position} fragment F5 on Cloudcast {_tags4ruy33:tags {...F4},id} fragment F6 on Cloudcast {restrictedReason,owner {username,isSubscribedTo,isViewer,id},slug,id,isAwaitingAudio,isDraft,isPlayable,streamInfo {hlsUrl,dashUrl,url,uuid},audioLength,currentPosition,proportionListened,repeatPlayAmount,seekRestriction,previewUrl,isExclusivePreviewOnly,isExclusive,picture {primaryColor,isLight,_primaryColor2pfPSM:primaryColor(lighten:$lighten_2),_primaryColor3Yfcks:primaryColor(alpha:$alpha_3)}} fragment F7 on Cloudcast {id,name,slug,owner {id,username,displayName,isSelect,...F1,...F2},isUnlisted,isExclusive,...F3,...F5,...F6} fragment F8 on Cloudcast {isDraft,hiddenStats,plays,publishDate,qualityScore,listenerMinutes,id} fragment F9 on Cloudcast {id,isFavorited,isPublic,hiddenStats,favorites {totalCount},slug,owner {id,isFollowing,username,displayName,isViewer}} fragment Fa on Cloudcast {id,isReposted,isPublic,hiddenStats,reposts {totalCount},owner {isViewer,id}} fragment Fb on Cloudcast {id,isUnlisted,isPublic} fragment Fc on Cloudcast {id,isUnlisted,isPublic,slug,description,picture {urlRoot},owner {displayName,isViewer,username,id}} fragment Fd on Cloudcast {id,isPublic,isHighlighted,owner {isViewer,id}} fragment Fe on Cloudcast {id,isPublic,isExclusive,owner {id,username,isViewer,isSubscribedTo},...F8,...F9,...Fa,...Fb,...Fc,...Fd} fragment Ff on Cloudcast {owner {quantcastTrackingPixel,id},id} fragment Fg on Cloudcast {id,slug,name,isAwaitingAudio,isDraft,isScheduled,restrictedReason,publishDate,waveformUrl,audioLength,owner {username,id},picture {...F0},...F7,...Fe,...Ff} fragment Fh on User {id,displayName,username,_uploadsAlSUp:uploads(first:$first_0,after:\"YXJyYXljb25uZWN0aW9uOjk=\",orderBy:$orderBy_1) {edges {node {id,...Fg},cursor},pageInfo {endCursor,hasNextPage,hasPreviousPage}}}","variables":{"first_0":20,"lighten_2":15,"orderBy_1":"LATEST","alpha_3":0.3}}

    headers = {'Referer':'https://www.mixcloud.com/DETOX_INTOX/','X-Requested-With':'XMLHttpRequest','Content-Type':'application/json','X-CSRFToken':resp.cookies["csrftoken"]}

    response = requests.post(gurl,  data = json.dumps(data), headers = headers, cookies = resp.cookies)

    grajson = json.loads(response.content)
    for element in grajson['data']['_user1t8cpv']['_uploadsAlSUp']['edges']:
        hrefs.append("/" + grajson['data']['_user1t8cpv']['username'] + "/" + urllib.parse.quote(element['node']['slug']) + "/")
    
    return hrefs

url = sys.argv[1]
urllen = (len(url.split("/")))

if urllen == 6: # Probably a single track
    download(url)
elif urllen == 5: # Probably an artist page
    hrefs = getMultiple(url)
    for href in hrefs:
        print(href)
        download("http://mixcloud.com" + href)
