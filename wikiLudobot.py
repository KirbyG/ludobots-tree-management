    # Procedure:
    #
    # 1) check new posts
    # 2) if post is not in the database of viewed posts...
    #     a) add post to list of viewed posts
    #     b) if post tag signifies it is a new Project...
    #         I) create associated wiki page with page-name = post-id
    #         II) wiki page links to original post
    #         III) bot messages creator of post to...
    #             firstly) add link to associated wiki page in the original post
    #             secondly) fill in the details of their proposed Project in the wiki
    #             thirdly) add "from" and "to" tags to the wiki page

import praw
from pprint import pprint
import re
import time
from time import gmtime, strftime
import HTMLParser
import os
import sys
import traceback

########################################################################
retries = 3
def updateLog(string):
    print string
    header = "###############################\n##  wikiLudobot's Error Log  ##\n###############################\n\n"

    timestring = time.strftime("%m/%d/%Y %H:%M - ", time.gmtime())
    
    dir = os.path.dirname(__file__)
    filename = os.path.join(dir, 'wikiLudobot_log.txt')    
    
    log = open(filename, "r")
    logData = log.read()
    logData = logData.replace(header, "")
    log.close()

    log_w = open(filename, "w")
    log_w.write(header+timestring+string+"\n"+logData)
    log_w.close()

########################################################################

def attempt(function, actionMessage, doexit=True):
    attempts = 0
    output = False
    while attempts < retries:
        attempts += 1
        try:
            output = function()
            break
        except:
            updateLog("retry: " + actionMessage)
            time.sleep(5)
    if attempts == retries:
        updateLog("Error: " + actionMessage)
        if doexit:
            sys.exit()
    return output

r = attempt(lambda: praw.Reddit('/r/ludobots treeLudobot UVM'), "connect to reddit")
attempt(lambda: r.login("wikiLudobot", "nikolatesla"), "log in to reddit")
ludobots = attempt(lambda: r.get_subreddit("ludobots"), "get /r/ludobots objects")

global memData, users
memData = ""
users = []


h = HTMLParser.HTMLParser()

###################################################################################

def getTagAndTitle(title):  # Takes post title in form "[Tag] This is a Title", returns list ["Tag", "This is a Title"]
    start = title.find("[")
    end = title.find("]")
    if start < len(title)-1 and start != -1 and end != -1:
        tag = title[start+1:end]
        if len(tag) == 0:
            tag = "None"
    else:
        tag = "None"
    if end < len(title) - 1:
        newtitle = title[end+1:]
        while newtitle[0] == " ":
            newtitle = newtitle[1:]
            if len(newtitle) == 0:
                break
    else:
        newtitle = ""
    return [tag, newtitle]

def wikiExists(wiki):  # True/False: checks if wiki page exists
    try:
        r.get_wiki_page(ludobots, wiki)
    except:
        return False
    return True;
    '''print wiki
    r.get_wiki_page(ludobots, wiki)
    #pprint(r.get_wiki_pages(ludobots))
    #pprint("these are the wiki pages:" + str(r.get_wiki_pages(ludobots)))
    return False
    try:
        print str(ludobots) + " " + str(wiki)
        pprint("these are the wiki pages:" + str(r.get_wiki_pages(ludobots)))
        #r.get_wiki_page(ludobots, wiki)
        print r + "this is the wiki page"
    except:
        print "about to return false"
        return False
    print "no issues loading wiki page"
    return True'''

def createBlankWiki(wiki, override=False):  # creates a blank new wiki page as /r/ludobots/wiki/*name*
    if override or not wikiExists(wiki):
        editWikiPage(wiki, "")
        return True
    else:
        print "Warning: Attempted to Overwrite wiki page: '"+wiki+"'"
    return False

def urlText(string):
    swaps = [[" ", "%20"], ["#", "%23"], ["$", "%24"], ["&", "%26"], ["'", "%27"], ["(", "%28"], [")", "%29"],
             ["*", "%2A"], ["+", "%2B"], [",", "%2C"], ["/", "%2F"], [":", "%3A"], [";", "%3B"], ["=", "%3D"],
             ["?", "%3F"], ["@", "%40"], ["[", "%5B"], ["]", "%5D"]]
    for pair in swaps:
        while string.find(pair[0]) != -1:
            string = string.replace(pair[0], pair[1])

    return string

def createProjectWiki(post):  # creates a wiki project page for corresponding user-post
    tag, title = getTagAndTitle(post.title)
    
    attempt(lambda: post.set_flair(flair_css_class=tag.lower()), "set post flair for post")
        
    commentText = "Hey " + str(post.author) + ", thanks for submitting your Project idea! This is just a friendly "
    commentText += "reminder to edit this post to include a link to the new [Project Wiki Page]("
    commentText += "http://www.reddit.com/r/ludobots/wiki/" + str(post.id) + ") that we're making for this project. "
    commentText += "The Wiki Page will be automatically created within a couple minutes. Here's its URL, so you can "
    commentText += "add that link in the meantime:\r\n\r\n    http://www.reddit.com/r/ludobots/wiki/" + str(post.id)

    attempt(lambda: post.add_comment(commentText), "add comment to post in createProjectWiki() for post " + str(post.title))

    body = post.selftext
    id = post.id
    author = post.author
    titleURL = urlText(title)

    wikiContent = "Prerequisites: [***please add a link to the project wiki that this project is inspired by***]"
    wikiContent += "\r\n\r\n[The Course Tree](http://www.reddit.com/r/ludobots/wiki/tree)"
    wikiContent += "\r\n\r\nNext Steps: [***this field is optional, please erase this text regardless***]"
    wikiContent += "\r\n\r\n***\r\n\r\n"
    wikiContent += "[](http://www.reddit.com/r/ludobots/submit?selftext=true;title=%5BSubmission%5D%20My%20"
    wikiContent += "Work%20Submission%20for%20Project:%20\"" + titleURL + "\";text=for:%20%5B"
    wikiContent += titleURL + "%5D%28http://www.reddit.com/r/ludobots/wiki/" + str(id) + "%29%0A%0A%28work submission "
    wikiContent += "details/urls here%29)\r\n\r\n***\r\n\r\n"
    wikiContent += "###" + str(title) + "\r\n\r\ncreated: " + strftime("%I:%M %p, %m/%d/%Y", gmtime())
    wikiContent += "\r\n\r\n***[Discuss this Project](http://www.reddit.com/r/ludobots/comments/" + str(id) + ")***"
    wikiContent += "\r\n\r\n***\r\n\r\n####Project Description"
    wikiContent += "\r\n\r\n" + str(body) + "\r\n\r\n***\r\n\r\n"
    wikiContent += "####Project Details\r\n\r\n***PROJECT CREATOR (" + str(author) + ") - PLEASE ADD PROJECT "
    wikiContent += "INFORMATION HERE BY EDITING THIS WIKI PAGE***\r\n\r\n*This section may include step by step "
    wikiContent += "instructions, links to images or other relevant content, project goals and purpose, and guidelines "
    wikiContent += "for what constitutes a valid user work submission for the project.*\r\n\r\n"
    wikiContent += "***\r\n\r\n####Common Questions "
    wikiContent += "([Ask a Question](http://www.reddit.com/r/ludobots/submit?selftext=true;title=%5BQuestion%5D%20"
    wikiContent += "Question%20Title%20Here;text=for:%20%5B" + titleURL + "%5D%28http://www.reddit.com/r/ludobots/wiki/"
    wikiContent += str(id) + "%29%0A%0A%28question%20details%20here%29))"
    wikiContent += "\r\n\r\nNone so far.\r\n\r\n***\r\n\r\n####Resources "
    wikiContent += "([Submit a Resource](http://www.reddit.com/r/ludobots/submit?selftext=true;title=%5BResource%5D%20"
    wikiContent += "Resource%20Title%20Here;text=for:%20%5B" + titleURL + "%5D%28http://www.reddit.com/r/ludobots/wiki/"
    wikiContent += str(id) + "%29%0A%0A%28resource%20information/urls%20here%29))\r\n\r\nNone."

    wikiContent += "\r\n\r\n***\r\n\r\n####User Work Submissions\r\n\r\nNo Submissions"
    editWikiPage(id, wikiContent)

    projects = attempt(lambda: r.get_wiki_page(ludobots, "ludobots_projectdata").content_md, "load wiki page ludobots_projectdata in createProjectWiki for post " + str(post.title))

    editWikiPage("ludobots_projectdata", projects+","+id)

    message = "Hi " + str(author) + "! Thanks for submitting a proposal for your Project Idea entitled \""
    message += str(title) + "\". We've created a wiki page for your project at /r/ludobots/wiki/" + (id) + ". "
    message += "It is now your responsibility to set up your project's wiki page so it may be properly "
    message += "incorporated into the Ludobots Curriculum and so other users may access it. "
    message += "Here are the absolutely crucial steps involved in doing so:\r\n\r\n"
    message += "**1)** Copy the above URL to the wiki page and edit your original post to link to that URL\r\n\r\n"
    message += "**2)** Determine which project(s) your project is based upon or inspired by, and add the URL(s) of those projects' "
    message += "corresponding wiki pages in the form of \"from\" tags (from: url_1, url_2, etc) at the VERY top "
    message += "of your project's wiki page. Try to make these URLs into links with relevant page titles\r\n\r\n"
    message += "**3)** Optionally, you may choose to add \"to\" tags as well, although you may also simply leave this field "
    message += "blank. Use a \"to\" tag when there is a project you specifically intend for users to work on "
    message += "after completing your Project.\r\n\r\n"
    message += "**4)** Lastly, and most importantly, go to the wiki page of your new project and fill in the project "
    message += "details. This might include more information about the project, step-by-step instructions, your own "
    message += "hypotheses and reasons for creating the Project, images, links, a conclusion/goal for other users "
    message += "who are attempting your project, etc. Be as specific and detailed as possible, without giving away too "
    message += "much information about your own findings (you can post findings in the corresponding post you created "
    message += "for the project). If you would like to include images in your wiki, hang tight as this is not yet possible.\r\n\r\n"
    message += "Please do not reply to this message, as this inbox is not monitored. For all questions and inquiries, "
    message += "please message /u/snaysler, creator of the Ludobots MOOC."

    attempt(lambda: r.send_message(author, "Important Information For Creating Your New Project Page", message), "send project page creation information message in createProjectWiki() for post " + str(post.title))

    print "Messaging " + str(author) + " about how to set up his newly generated wiki page at /wiki/" + str(id)

    announcement = "[" + str(author) + "](http://www.reddit.com/r/ludobots/wiki/" + str(author) + ") just created "
    announcement += "a [New Project](http://www.reddit.com/r/ludobots/wiki/" + id + ")"

    announce(announcement)


def createHypothesisWiki(post): #creates a wiki hypothesis page for a hypothesis posed in a user's post
    tag, title = getTagAndTitle(post.title)
    body = post.selftext
    id = post.id
    author = post.author
    wikiContent = "Prerequisites:\r\n\r\nNext Steps:\r\n\r\n***\r\n\r\n###"
    wikiContent += str(title) + "\r\n\r\n*[Discuss this Hypothesis](http://www.reddit.com/r/ludobots/comments/" + str(id) + ")"
    wikiContent +=  "*\r\n\r\n***\r\n\r\n" + "####Hypothesis Description" + "\r\n\r\n" + str(body)
    wikiContent +=  "\r\n\r\n***\r\n\r\n" + "####Experimental Steps\r\n\r\n***PROJECT CREATOR (" + str(author) + ") - PLEASE ADD INFORMATION ABOUT IMPLEMENTATION OF HYPOTHESIS TESTING HERE BY EDITING THIS WIKI PAGE***\r\n\r\n"
    wikiContent += "\r\n\r\nSubmission information: Submit final data from trials (only one number per trial!) as a list of number separated by strings by messaging resultsBot. "
    wikiContent += "In the subject the message, include the id of this experiment, " + str(id) + ", and the title of the group you are submitting as it appears in Experimental Groups. "
    wikiContent += "For example, a message subject to resultsBot could be *123abc, group1*, and the body, with the data, could be *11.2, 3.4, 19.5* "
    wikiContent += "\r\n\r\n***\r\n\r\n####Experimental Groups\r\n\r\n " + "group1:\r\n\r\ngroup2:\r\n\r\n***PROJECT CREATOR (" + str(author) + ") - PLEASE CHANGE GROUP NAMES SO THAT THEY ARE RELEVANT TO YOUR HYPOTHESIS! Remember, groups must not contain whitespace characters (they can't have spaces in them)***\r\n\r\n "
    wikiContent += "\r\n\r\n***\r\n\r\n####Conclusions\r\n\r\nThere is insufficient data for a conclusion."
    editWikiPage(id, wikiContent)

    hypotheses = attempt(lambda: r.get_wiki_page(ludobots, "hypothesis_data").content_md, "load wiki page hypothesis_data in createHypothesisWiki() for post " + str(post.title))

    editWikiPage("hypothesis_data", hypotheses +'\r\n\r\n'+id+":group1:/;group2:/;~", ludobots)

    message = "Hi " + str(author) + "! You just took the next step with ludobots by submitting your own hypothesis for the community to research, "
    message += "titled \"" + str(title) + "\". We've made a wiki for your hypothesis at /r/ludobots/wiki/" + id +" , which will be where people find out about the project and how to "
    message += "submit their results. The page will also display the conclusion of the research when enough data has been added! \r\n\r\nIt's important "
    message += "that you add several things so others can be involved in the experiment: \r\n\r\n"
    message += "**1)** Copy the wiki page URL above and edit your original post to link to that URL\r\n\r\n"
    message += "**2)** Determine which project(s) your experiment is based upon or inspired by, and add the URL(s) of those projects "
    message += "to your wiki page in the \"from\" tags at the VERY top. It is best to make the links meaningful page titles. This will allow your hypothesis to be included in the wiki tree. \r\n\r\n"
    message += "**3)** In your wiki page, edit the Experimental Groups section so that the group names are relevant to your experiment. This is very important for user submissions! Remeber, you should "
    message += "one control group and one experimental group, and you need to leave a colon after the group name that you pick.\r\n\r\n"
    message += "**4)** Add to the Description and Steps sections of your wiki to give other reserachers enough information to implement your experimental method "
    message += "and provide accurate results to your experiment. Remember to add information to the Submission step, to tell reserchers what data they should submit. "
    message += "Remember that submission data must be one number for each trial. For example, if you are running 30 hillclimbers and gathering the best fitness "
    message += "of each, one hillclimber would be a single trial and the best fitness would be the data point for that trial. Users can submit data for a bunch of "
    message += "trials in a single message to resultsBot, but they can't submit more than one data point for a single trial. \r\n\r\n"
    message += "Some final things to remember: Don't tell other researchers your own results for your hypothesis, as that might bias them. You can and should "
    message += "submit your own results to resultsBot, though, *after* you set up your wiki. "

    attempt(lambda: r.send_message(author, "Important Information For Creating Your New Hypothesis Page", message), "send hypothesis wiki creation information message in createHypothesisWiki() for post " + str(post.title))

    print "Messaging " + str(author) + " about how to set up their newly generated wiki page at /wiki/" + str(id)

def existsInDatabase(term, memory=True):  # True/False: whether string 'term' exists in database page at /wiki/data
    term = str(term)
    if memory:  # search database content stored in global variable memData to avoid over-accessing reddit
        global memData
        if len(memData) < 1:
            memDataDownload()
        database = memData
    else:
        database = attempt(r.get_wiki_page(ludobots, "data").content_md.encode("ascii", "ignore"), "load wiki page wikiludobot in existsInDatabase() for term " + str(term))

    if database.find(term) == -1:
        return False
    return True

def getDatabaseVar(var, memory=True):
    if memory:
        global memData
        if len(memData) < 1:
            memDataDownload()
        database = memData
    else:
        database = attempt(lambda: r.get_wiki_page(ludobots, "data").content_md, "load wiki page data in getDatabaseVar() for var " + str(var))

    if database.find(var) == -1:
        return None
    marker = database.find(var) + len(var) + 1
    markerEnd = marker + database[marker:].find("\r\n\r\n")
    if markerEnd > marker:
        varData = database[marker:markerEnd]
    else:
        varData = database[marker:]
    return varData

def setDatabaseVar(var, value, memory=True):
    if memory:
        global memData
        if len(memData) < 1:
            memDataDownload()
        database = memData
    else:
        database = attempt(lambda: r.get_wiki_page(ludobots, "data").content_md, "load wiki page data in setDatabaseVar() for var " + str(var))

    if database.find(var) == -1:
        return False

    marker = database.find(var) + len(var) + 1
    markerEnd = marker + database[marker:].find("\r\n\r\n")
    database = database[:marker] + str(value) + database[markerEnd:]
    if memory:
        memData = database
    else:
        editWikiPage("data", database)
    return True

def addItemToDatabase(item, type, memory=True):
    if memory:
        global memData
        if len(memData) < 1:
            memDataDownload()
        marker = memData.find(type) + len(type) + 1
        memData = memData[:marker] + item + "," + memData[marker:]
    else:
        database = r.get_wiki_page(ludobots, "data").content_md
        marker = database.find(type) + len(type) + 1
        database = database[:marker] + item + "," + database[marker:]
        editWikiPage("data", database)

def memDataDownload():
    global memData

    memData = attempt(lambda: r.get_wiki_page(ludobots, "data").content_md, "load wiki page data in memDataDownload()")

def memDataUpload():
    global memData
    temp = memData
    print "Uploading..."
    attempt(lambda: r.edit_wiki_page(ludobots, "data", memData), "edit wiki page data in memDataUpload()")

def addReferenceFrom(wiki, refWiki):
    wikiData = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in addReferenceFrom()")

    if wikiData.find("from:") == -1:
        return False
    marker = wikiData.find("Prerequisites:") + len("Prerequisites:")

    refWikiData = r.get_wiki_page(ludobots, refWiki).content_md
    titleMarker_start = refWikiData.find("###") + len("###")
    titleMarker_finish = titleMarker_start + refWikiData[titleMarker_start:].find("\r\n\r\n")
    refTitle = refWikiData[titleMarker_start:titleMarker_finish]
    if len(refTitle) < 4 or refWikiData.find("###") == -1:
        refTitle = refWiki

    wikiData = wikiData[:marker] + " [**" + refTitle + "**](http://www.reddit.com/r/ludobots/wiki/" + refWiki + ")" + wikiData[marker:]

    editWikiPage(wiki, wikiData)

def addReferenceTo(wiki, refWiki):
    wikiData = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in addReferenceTo()")

    if wikiData.find("Next Steps:") == -1:
        return False
    marker = wikiData.find("Next Steps:") + len("Next Steps:")


    refWikiData = r.get_wiki_page(ludobots, refWiki).content_md
    titleMarker_start = refWikiData.find("###") + len("###")
    titleMarker_finish = titleMarker_start + refWikiData[titleMarker_start:].find("\r\n\r\n")
    refTitle = refWikiData[titleMarker_start:titleMarker_finish]
    if len(refTitle) < 4 or refWikiData.find("###") == -1:
        refTitle = refWiki

    wikiData = wikiData[:marker] + " [ [**" + refTitle + "**](http://www.reddit.com/r/ludobots/wiki/" + refWiki + ") ]" +  wikiData[marker:]

    editWikiPage(wiki, wikiData)

def getTimestamp():
    #return 1441229740
    timestamp = attempt(lambda: float(r.get_wiki_page(ludobots, "wikiludobotdata").content_md), "load timestamp in getTimestamp()")
    return timestamp

def checkForNewPosts():  # checks to see if there are new project proposals to wikify
    print 'enter check for new posts'
    timestamp = getTimestamp()

    safeguard = []

    mcLudobotQuestions = ""
    newposts = attempt(lambda: ludobots.get_new(limit=30), "get new posts in ludobots in checkForNewPosts()")

    print "Checking for new posts..."

    first = True
    newtimestamp = 0
    for post in newposts:  # for all new posts
        if not wikiExists(str(post.author)):
            print "wiki didn't exist"
            createUserProfile(post.author)
            #print "sleeping30: wiki didn't exist"
            time.sleep(30)
        if post.created_utc > timestamp:  # if a post hasn't been seen before by this bot
            print 'found a new post'
            if first:
                newtimestamp = post.created_utc
                first = False
            print "Checking new post: '" + post.title + "'"
            postTag, postName = getTagAndTitle(post.title)  # extract the post's Tag and Name from the title
            if postTag == "Project" or postTag == "project":  # if the post is a new user-proposed project
                createProjectWiki(post)
            elif postTag == "Submission" or postTag == "submission":
                selftext = post.selftext
                links = findLinks(selftext)
                if links:
                    ludobotsLinks = filterLinksByDomain(links, "reddit.com/r/ludobots/wiki")
                    if ludobotsLinks == []:
                        links = False
                    else:
                        wiki = extractWikiId(ludobotsLinks[0])
                        temp = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in checkForNewPosts()")
                recipient = post.author
                if not links or not wikiExists(wiki) or temp.find("User Work Submissions\r\n\r\n") == -1:
                    message = "Hi " + str(recipient) + ", thanks for making a submission, but unfortunately we aren't "
                    message += "sure what Project you are trying to submit work for. Please make certain that you "
                    message += "include the full url of the wiki page for the Project your work is about in your "
                    message += "post. Also, please make certain that this url is the VERY first url mentioned in your "
                    message += "post, or the bots will not be able to process your submission.\r\n\r\n**Here's how "
                    message += "to proceed:**\r\n\r\n* Go to your submission post, and below your post hit the ***edit"
                    message += "*** button, then ***copy*** all the text in your post from this field\r\n\r\n* Next, "
                    message += "you will need to ***delete your post*** entirely and make a ***new post***. Next to the button"
                    message += " for editing your post there should be a button to delete your post, removing it "
                    message += "permanently from the subreddit. You have to delete it (instead of simply editing it) "
                    message += "because the bots only give a post one look, and if the post has an error in formatting "
                    message += "like yours does, it will exile it from further consideration.\r\n\r\n* The last step is "
                    message += "to recreate a new submission post, and paste the text from your first post into the new "
                    message += "one, making sure to include the Project wiki url at the top of the post before "
                    message += "resubmitting it.\r\n\r\nWithin a couple minutes, you should receive a message from "
                    message += "wikiLudobot confirming your successful submission, and a link to your work will be "
                    message += "added to the Project Wiki Page and your Profile Page.\r\n\r\nThanks,\r\n\r\nwikiLudobot"
                    if recipient in safeguard:
                        pass
                        #print "waiting 30 seconds to send message to user " + str(recipient)
                        #time.sleep(30)modded

                    attempt(lambda: r.send_message(recipient, "Sorry, your submission is incomplete!", message), "send incomplete message notification in checkForNewPosts()")
                    safeguard.append(recipient)
                    print "User '" + str(recipient) + "' improperly made a Project Submission. Message sent."
                else:
                    flair = post.link_flair_css_class
                    if flair != postTag.lower():
                        attempt(lambda: post.set_flair(flair_css_class=postTag.lower()), "set post flair for post " + str(post.title) + " to " + postTag.lower() + " in checkForNewPosts()")

                    addSubmissionToProjectWiki(wiki, post.id, post.author)
                    addSubmissionToProfile(wiki, post.id, post.author)
                    mcLudobotQuestions += str(recipient) + "," + str(wiki) + "\r\n\r\n"
                    message = "Hi, " + str(recipient) + ". Thanks for submitting your work for the Project entitled \""
                    message += getWikiTitle(wiki) + "\". We have included a link to your work at the bottom of the "
                    message += "Project's Wiki Page under the User Work Submissions section "
                    message += "[Here](http://www.reddit.com/r/ludobots/wiki/" + wiki + "#wiki_user_work_submissions). Other users will"
                    message += " likely view and comment on your work.\r\n\r\nAdditionally, we have added this "
                    message += "submission to your [Profile Page](http://www.reddit.com/r/ludobots/wiki/" + str(recipient)
                    message += ")\r\n\r\nCheers,\r\n\r\nwikiLudobot"
                    if recipient in safeguard:
                        print "waiting 30 seconds to send message to user " + str(recipient)
                        print "sleeping30: user formatting"
                        time.sleep(30)
                    attempt(lambda: r.send_message(recipient, "Thank you for submitting your work!", message), "send thank you for submitting work submission message in checkForNewPosts()")

                    safeguard.append(recipient)
                    print "User '" + str(recipient) + "' just submitted work for Project '" + getWikiTitle(wiki) + "'."
            elif postTag == "Question" or postTag == "question":
                selftext = post.selftext
                links = findLinks(selftext)
                if links:
                    ludobotsLinks = filterLinksByDomain(links, "reddit.com/r/ludobots/wiki")
                if ludobotsLinks:
                    wiki = extractWikiId(ludobotsLinks[0])
                else:
                    print "no ludobots links"
                    links = False

                recipient = post.author
                tempPage = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in checkForNewPosts()")

                if not links or not wikiExists(wiki) or tempPage.find("####Common Questions") == -1:
                    message = "Hi " + str(recipient) + ", thanks for submitting a Question, but unfortunately there is "
                    message += "a problem with your project reference. Make sure you have included in your post the url"
                    message += " to the wiki page for the project you are asking a question about. Also, make sure that"
                    message += " the url is the FIRST url mentioned in your post, or the bots won't know which project "
                    message += "you mean to submit a question for. Please **delete** your post, and make a **new** "
                    message += "one that follows this format. Simply editing the post you already made will not work. "
                    message += "\r\n\r\nCheers,\r\n\r\nwikiLudobot"
                    if recipient in safeguard:
                        print "waiting 30 seconds to send message to user " + str(recipient)
                        print "sleeping30: user formatting error"
                        time.sleep(30)
                    attempt(lambda: r.send_message(recipient, "There was a problem with the Question you submitted!", message), "send question submission error message in checkForNewPosts()")

                    safeguard.append(recipient)
                    print "User '" + str(recipient) + "' just submitted a Question without referencing a project. Message sent."
                else:
                    attempt(lambda: post.set_flair(flair_css_class=postTag.lower()), "set post flair for post " + str(post.title) + " to " + postTag.lower() + " in checkForNewPosts()")

                    addQuestionToProjectWiki(wiki, post.id, recipient)
                    message = "Hi, " + str(recipient) + "! Thank you for submitting your question on the Project "
                    message += "entitled \"" + getWikiTitle(wiki) + "\". It has been [Added to the Project Wiki]"
                    message += "(http://www.reddit.com/r/ludobots/wiki/" + str(wiki) + "#wiki_common_questions). "
                    message += "Users should now be able to see your question, and answer it for you.\r\n\r\n"
                    message += "Cheers,\r\n\r\nwikiLudobot"
                    if recipient in safeguard:
                        print "waiting 30 seconds to send message to user " + str(recipient)
                        print "sleeping30: user formatting error"
                        time.sleep(30)
                    attempt(lambda: r.send_message(recipient, "Your Question has been successfully submitted!", message), "send successful question submission message in checkForNewPosts()")

                    safeguard.append(recipient)
                    print "User '" + str(recipient) + "' just submitted a Question for wiki: " + str(wiki)
            elif postTag == "Resource" or postTag == "resource":
                selftext = post.selftext
                links = findLinks(selftext)
                if links and len(links) >= 2:
                    ludobotsLinks = filterLinksByDomain(links, "reddit.com/r/ludobots/wiki")
                    wiki = extractWikiId(ludobotsLinks[0])
                recipient = post.author
                if not links or len(links) < 2 or not wikiExists(wiki) or r.get_wiki_page(ludobots, wiki).content_md.find("####Resources") == -1:
                    message = "Hi " + str(recipient) + ", thanks for submitting a Resource, but unfortunately there is "
                    message += "a problem with your project reference. Make sure you have included in your post the url"
                    message += " to the wiki page for the project you are submitting a resource for. Also, make sure that"
                    message += " this url is the FIRST url mentioned in your post, or the bots won't know which project "
                    message += "you mean to submit a resource for. Please **delete** your post, and make a **new** "
                    message += "one that follows this format. Simply editing the post you already made will not work. "
                    message += "\r\n\r\nCheers,\r\n\r\nwikiLudobot"
                    if recipient in safeguard:
                        print "waiting 30 seconds to send message to user " + str(recipient)
                        print "sleeping30: user formatting error"
                        time.sleep(30)
                    attempt(lambda: r.send_message(recipient, "There was a problem with the Resource you submitted!", message), "send resource submission error message in checkForNewPosts()")

                    safeguard.append(recipient)
                    print "User '" + str(recipient) + "' just submitted a Resource without referencing a project. Message sent."
                else:
                    post.set_flair(flair_css_class=postTag.lower())
                    addResourceToProjectWiki(wiki, post.id, recipient)
                    message = "Hi, " + str(recipient) + "! Thank you for submitting a Resource for the Project "
                    message += "entitled \"" + getWikiTitle(wiki) + "\". It has been [Added to the Project Wiki]"
                    message += "(http://www.reddit.com/r/ludobots/wiki/" + str(wiki) + "#wiki_resources). "
                    message += "\r\n\r\nCheers,\r\n\r\nwikiLudobot"
                    if recipient in safeguard:
                        print "waiting 30 seconds to send message to user " + str(recipient)
                        print "sleeping30: user formatting error"
                        time.sleep(30)
                    attempt(lambda: r.send_message(recipient, "Your Resource has been successfully submitted!", message), "send successful resource submission message in checkForNewPosts()")

                    safeguard.append(recipient)
                    print "User '" + str(recipient) + "' just submitted a Resource for wiki: " + str(wiki)
            elif postTag == "Hypothesis" or postTag == "hypothesis":
                createHypothesisWiki(post)
    print "Done Checking Posts."
    if newtimestamp != 0:
        attempt(lambda: r.edit_wiki_page(ludobots, "wikiludobotdata", str(newtimestamp)), "upload timestamp in checkForNewPosts()")


def addQuestionToProjectWiki(wiki, post, author):
    wikiPage = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in addQuestionToProjectWiki()")

    signifier = "####Common Questions"
    marker = wikiPage.find(signifier)
    searchingText = wikiPage[marker:]
    marker += searchingText.find("\r\n\r\n") + len("\r\n\r\n")
    preText = wikiPage[:marker]
    tempText = wikiPage[marker:]
    tempMarker = tempText.find("***")
    if marker == -1 or tempMarker == -1:
        print "Attempted to add Question to Project Wiki, but there is a formatting error to Wiki Page " + str(wiki)
        return False
    questionText = tempText[:tempMarker]
    postText = tempText[tempMarker:]
    if not findLinks(questionText):
        questionText = ""
    questionText += "[" + attempt(lambda: getTagAndTitle(r.get_submission(submission_id=post).title)[1], "load submission " + str(post) + " in addQuestionToProjectWiki()") + "](http://www.reddit.com"
    
    questionText += "/r/ludobots/comments/" + str(post) + ")\r\n\r\n"
    newWiki = preText + questionText + postText
    editWikiPage(wiki, newWiki)

    announcement = "[" + str(author) + "](http://www.reddit.com/r/ludobots/wiki/" + str(author) + ") submitted a "
    announcement += "[Question](http://www.reddit.com/r/ludobots/comments/" + str(post) + ") for a [Project]"
    announcement += "(http://www.reddit.com/r/ludobots/wiki/" + str(wiki) + ")"
    announce(announcement)

def addResourceToProjectWiki(wiki, post, author):
    wikiPage = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in addResourceToProjectWiki()")

    signifier = "####Resources"
    marker = wikiPage.find(signifier) + len(signifier)
    searchingText = wikiPage[marker:]
    marker += searchingText.find("\r\n\r\n") + len("\r\n\r\n")
    preText = wikiPage[:marker]
    tempText = wikiPage[marker:]
    tempMarker = tempText.find("***")
    if marker == -1 or tempMarker == -1:
        print "Attempted to add Resource to Project Wiki, but there is a formatting error to Wiki Page " + str(wiki)
        return False
    resourceText = tempText[:tempMarker]
    postText = tempText[tempMarker:]
    if not findLinks(resourceText):
        resourceText = ""
    resourceText += "[" + attempt(lambda: getTagAndTitle(r.get_submission(submission_id=post).title)[1], "load submission " + str(post) + " in addResourceToProjectWiki()") + "[("

    resourceText += "http://www.reddit.com/r/ludobots/comments/" + str(post) + ")\r\n\r\n"
    newWiki = preText + resourceText + postText
    editWikiPage(wiki, newWiki)

    announcement = "[" + str(author) + "](http://www.reddit.com/r/ludobots/wiki/" + str(author) + ") submitted a "
    announcement += "[Resource](http://www.reddit.com/r/ludobots/comments/" + str(post) + ") for a [Project]"
    announcement += "(http://www.reddit.com/r/ludobots/wiki/" + str(wiki) + ")"
    announce(announcement)

def getWikiTitle(wiki):
    wiki = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in getWikiTitle()")

    signifier = "###"
    marker = wiki.find(signifier) + len(signifier)
    markerEnd = marker + wiki[marker:].find("\r\n\r\n")
    if marker == -1:
        return "Undefined Page Title"
    return wiki[marker:markerEnd]

def announce(text):
    sidebar = attempt(lambda: r.get_wiki_page(ludobots, "config/sidebar").content_md, "load wiki page config/sidebar in announce()")
    #print sidebar
    signifier = "###Live Feed:\r\n"
    if sidebar.find(signifier) == -1:
        print "Error adding announcement to Live Feed: \"" + text + "\""
        return False
    marker = sidebar.find(signifier) + len(signifier)
    preText = sidebar[:marker]
    feed = sidebar[marker:]
    feedList = feed.split("\r\n\r\n")
    feedList.insert(0, text)
    newfeed = ""
    for i in range(0, min(20, len(feedList))):
        newfeed += feedList[i] + "\r\n\r\n"
    newSidebar = preText + newfeed
    editWikiPage("config/sidebar", newSidebar, doexit=False)

def addSubmissionToProfile(wiki, post, author):
    if not wikiExists(str(author)):
        createUserProfile(str(author))
        print "Created User Profile for " + str(author) + ", waiting 30 seconds to modify it..."
        time.sleep(30)
    def f():
        print wikiExists(str(author))
        return r.get_wiki_page(ludobots, str(author))
    profilePage = attempt(lambda: r.get_wiki_page(ludobots, str(author)).content_md, "load wiki page " + str(author) + " in addSubmissionToProfile()")

    signifier = "######Completed Projects:\r\n\r\n"
    projectsIndex = profilePage.find(signifier) + len(signifier)
    preText = profilePage[:projectsIndex]
    tempText = profilePage[projectsIndex:]
    mcIndex = tempText.find("\r\n\r\n***")
    projects = tempText[:mcIndex]
    mcText = tempText[mcIndex:]
    if not findLinks(projects):
        projects = ""
    projects += "\r\n\r\n[" + getWikiTitle(wiki) + "](http://www.reddit.com/r/comments/" + post + ")"
    newProfile = preText + projects + mcText
    editWikiPage(str(author), newProfile)

def addSubmissionToProjectWiki(wiki, post, author):
    wikiPage = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in addSubmissionToProjectWiki()")

    signifier = "User Work Submissions\r\n\r\n"
    submissionIndex = wikiPage.find(signifier) + len(signifier)
    preText = wikiPage[:submissionIndex]
    submissions = wikiPage[submissionIndex:]
    if not findLinks(submissions):
        submissions = ""
    submissions = "[" + str(author) + "](http://www.reddit.com/r/ludobots/comments/" + str(post) + ") (UTC " + \
                  strftime("%I:%M %p, %m-%d-%Y", gmtime()) + ")\r\n\r\n" + submissions
    newWiki = preText + submissions
    editWikiPage(wiki, newWiki)
    announcement = "[" + str(author) + "](http://www.reddit.com/r/ludobots/wiki/" + str(author) + ") "
    announcement += "submitted [Work](http://www.reddit.com/r/comments/" + str(post) + ") for a [Project](http://www.reddit.com/r/ludobots/wiki/" + wiki + ")"
    announce(announcement)

def getHypotheses():
    data = attempt(lambda: r.get_wiki_page(ludobots, "hypothesis_data").content_md, "load wiki page hypothesis_data in getHypotheses()")

    lines = data.split("\r\n\r\n")
    hypotheses = []

    for line in lines:
        hypotheses.append(line[:line.find(":")])

    return hypotheses

def getNewWikiRevisions():
    projects = attempt(lambda: r.get_wiki_page(ludobots, "ludobots_projectdata").content_md.split(","), "load wiki page ludobots_projectdata in getNewWikiRevisions()")

    hypotheses = getHypotheses()

    latestTimestamp = float(getDatabaseVar("wikiEditTimeStamp"))
    revisions_raw = r.get_content("http://www.reddit.com/r/ludobots/wiki/revisions", limit=50)
    revisions = []

    firstItem = 42  # just a value placeholder for snatching the first (most recent) revision's timestamp

    pagesInList = ["42thisisaplaceholder42"]

    for revision in revisions_raw:
        if firstItem == 42:
            firstItem = revision
        page = revision["page"]
        timestamp = float(revision["timestamp"])
        if not (page == "data" or page == "config/stylesheet") and timestamp > latestTimestamp:
            if (page in projects or page in hypotheses) and page not in pagesInList:
                revisions.append(revision)
                pagesInList.append(page)

    setDatabaseVar("wikiEditTimeStamp", firstItem["timestamp"])
    memDataUpload()

    return revisions

def findLinks(text): #return a set of strings containing the full address of all urls/links within the self-text
    links = re.findall("(?:(?:http://www\.)|(?:https://www\.)|(?:http://)|(?:https://)|(?:www\.))(?:[a-zA-Z0-9-])+(?:\.[a-z]{2,3})+(?:[a-zA-Z0-9-_\.~!\*\?';:@&=\+\$,/%*])*", text)

    linklist = []
    linksExist = False
    for link in links:
        linklist.append(link.encode("ascii", "ignore"))
        linksExist = True

    if not linksExist:
        return False

    return linklist

def filterLinksByDomain(links, domain):
    newlinks=[]
    if not links:
        return newlinks
    for link in links:
        if domain in link:
            newlinks.append(link)
    return newlinks

def extractWikiId(url):
    index = url.find("wiki/") + len("wiki/")
    if index == -1:
        return ""
    return url[index:]

def getWikiRefs(wiki, var="Prerequisites:"):
    print wiki
    data = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in getWikiRefs() with var=" + var, doexit=False)
    if not data:
        return False
    if data.find(var) == -1:
        if var == "Prerequisites:":
            var = "Prerequisite:"
        elif var == "Next Steps:":
            var = "Next Step:"
        else:
            return False

    if data.find(var) == -1:
        return False

    marker = data.find(var) + len(var) + 1
    markerEnd = marker + data[marker:].find("\r\n\r\n")
    if markerEnd > marker:
        varData = data[marker:markerEnd]
    else:
        varData = data[marker:]

    links = findLinks(varData)

    refs = []

    if not links:
        return []

    for link in links:
        id = extractWikiId(link)
        if len(id) > 0:
            refs.append(id)

    return refs

def getWikiRefsFrom(wiki):
    return getWikiRefs(wiki)

def getWikiRefsTo(wiki):
    return getWikiRefs(wiki, var="Next Steps:")

def checkWikiRevisions():  # checks recently edited wiki pages, and updates tree formatting/data
    edits = getNewWikiRevisions()
    print "Found " + str(len(edits)) + " new wiki-page revisions. Processing changes..."
    updates = ["42thisaintgonnabeseen42", "42doesntmatterwhatyouputhere42"]

    for wikiPage in edits:
        wiki = wikiPage["page"]
        fromRefs = getWikiRefsFrom(wiki)
        toRefs = getWikiRefsTo(wiki)
        print wiki, " has from refs: ", fromRefs, ", and to refs: ", toRefs
        if type(fromRefs).__name__ != "NoneType":
            for fromRef in fromRefs:
                refToRefs = getWikiRefsTo(fromRef)
                if type(refToRefs).__name__ == "NoneType" or wiki not in refToRefs:
                    if fromRef in updates:
                        print "Waiting 30 seconds to revise /wiki/" + fromRef + "..."
                        time.sleep(30)
                    print "Adding \"to\" Reference from " + fromRef + " to " + wiki
                    addReferenceTo(fromRef, wiki)
                    updates.append(fromRef)

        if type(toRefs).__name__ != "NoneType":
            for toRef in toRefs:
                refFromRefs = getWikiRefsFrom(toRef)
                if type(refFromRefs).__name__ == "NoneType" or wiki not in refFromRefs:
                    if toRef in updates:
                        print "Waiting 30 seconds to revise /wiki/" + toRef + "..."
                        time.sleep(30)
                    print "Adding \"from\" Reference from " + toRef + " to " + wiki
                    addReferenceFrom(toRef, wiki)
                    updates.append(toRef)

    print "Finished processing changes for edited wiki-pages"

def editWikiPage(page, content, subreddit=ludobots, doexit=True):
    attempt(lambda: r.edit_wiki_page(subreddit, page, h.unescape(content)), "editing wiki page " + str(page) + " in editWikiPage()")

def downloadUserList():
    global users
    users = getDatabaseVar("User-Data").split(",")

def createUserProfile(_user):
    user = str(_user)
    template = "###User Profile: " + user + "\r\n\r\nJoined: " + strftime("%m/%d/%Y", gmtime()) + "\r\n\r\n***"
    template += "\r\n\r\n######Completed Projects:\r\n\r\nNone\r\n\r\n***\r\n\r\n######Multiple Choice Questions "
    template += "Answered:\r\n\r\nNone"
    attempt(lambda: r.edit_wiki_page(ludobots, user, template), "load wiki page " + str(user) + " in createUserProfile()")
    addItemToDatabase(user, "User-Data")


def updateTree():
    bad = "://www.reddit.com/r/ludobots/submit?selftext=true;title=%5BSubmission%5D%20My%20Work%20Submission%20for%20Project:%20"
    getWikiRefsFrom("core10")
    wikiPagesRaw = attempt(lambda: r.get_wiki_pages(ludobots), "getting all wiki pages in updateTree")
    wikiPages = [str(wikiPage)[9:] for wikiPage in wikiPagesRaw]
    for wikiPage in wikiPages:
        prereqs = getWikiRefsFrom(wikiPage)
        nextSteps = getWikiRefsTo(wikiPage)
        if prereqs:
            for prereq in prereqs:
                prereqNexts = getWikiRefsTo(prereq)
                if prereqNexts:
                    if not wikiPage in prereqNexts:
                        addReferenceTo(prereq, wikiPage)
                        print "added " + str(wikiPage) + " to the next steps of " + str(prereq)
        
        if nextSteps:
            for nextStep in nextSteps:
                nextStepPrereqs = getWikiRefsFrom(nextStep)
                if nextStepPrereqs:
                    if not wikiPage in nextStepPrereqs:
                        addReferenceFrom(nextStep, wikiPage)
                        print "added " + str(wikiPage) + " to the prereqs of " + str(nextStep)
#######################################################################
checkForNewPosts()
time.sleep(30)
#attempt(lambda: checkWikiRevisions(), "checking wiki revisions")

#update prereqs and next steps on all projects
updateTree()



#projects = attempt(lambda: r.get_wiki_page(ludobots, "ludobots_projectdata").content_md, "load wiki page ludobots_projectdata in createProjectWiki for post ")
#editWikiPage("ludobots_projectdata", projects+","+"core04u,core05u,core06u,core07u,core08u,core09u,core10u")