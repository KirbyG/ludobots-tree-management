#imports
import matplotlib
matplotlib.use('Agg')# THIS ALLOWS THE PROGRAM TO RUN ON A SERVER THAT DOESN'T HAVE A DISPLAY

import matplotlib.pyplot as plt
import networkx as nx
import os
import praw
import re
import time
from pprint import pprint
import copy
import math
import sys

#earlier variables
r = None
ludobots = None

#tree variables-tweak these to adjust the tree
minProjectRadius = 8 # smallest radius of a project node
maxProjectRadius = 20 # largest radius of a project node
submissionDispersion = 0.08 # changes how spread apart the user submission nodes are
submissionRadius = 3 # radius of user submission nodes
qrSize = 15 #radius of question and resource nodes
#colors
BLUE = (0.15, 0.15, 1.0) #used for project nodes
RED = (1.0, 0.06, 0.06) #used for submission nodes
LIGHT_GREEN = (0.15, 0.89, 0.07) #used for question nodes
DARK_GREEN = (0.11, 0.51, 0.06) #used for resource nodes
PURPLE = (25.0/255, 25.0/255, 112.0/255) #more blue than purple, user for the index

#wiki parser functions

retries = 3
def attempt(function, actionMessage):
    attempts = 0
    output = False
    while attempts < retries:
        attempts += 1
        try:
            output = function()
            break
        except:
            print "retry: " + actionMessage
            time.sleep(5)
    if attempts == retries:
        updateLog("Error: " + actionMessage)
    return output

def findLinks(text): #return a set of strings containing the full address of all urls/links within the self-text
    links = re.findall("(?:(?:http://www\.)|(?:https://www\.)|(?:http://)|(?:https://)|(?:www\.))(?:[a-zA-Z0-9-])+(?:\.[a-z]{2,3})+(?:[a-zA-Z0-9-_\.~!\*\?';:@&=\+\$,/%*\[\]])*", text)

    linklist = []
    linksExist = False
    for link in links:
        linklist.append(link.encode("ascii", "ignore"))
        linksExist = True

    if not linksExist:
        return False

    return linklist

def extractWikiId(url):
    index = url.find("wiki/") + len("wiki/")
    if index == -1:
        return ""
    return url[index:]

def getWikiRefs(wiki, var="Prerequisites:"):
    data = ""

    data = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in getWikiRefs()")
    #pprint(data)
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
    markerEnd = marker + data[marker:].find("\r\n\r\n") + 2
    if markerEnd > marker:
        varData = data[marker:markerEnd]
    else:
        varData = data[marker:]

    links = findLinks(varData)

    refs = []
    if not links:
        return refs

    for link in links:
        id = extractWikiId(link)
        if len(id) > 0:
            refs.append(id)

    return refs

def getWikiRefsFrom(wiki):
    return getWikiRefs(wiki)

def getWikiRefsTo(wiki):
    return getWikiRefs(wiki, var="Next Steps:")

def getProjectSubmissions(wiki):
    wikiPage = ""

    wikiPage = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md.encode("ascii", "ignore"), "load wiki page " + str(wiki) + " in getProjectSubmissions()")

    signifier = "####User Work Submissions\r\n\r\n"
    marker = wikiPage.find(signifier)
    if marker == -1:
        return []
    else:
        marker += len(signifier)
    submissionText = wikiPage[marker:]

    submissionsList = submissionText.split("\r\n\r\n")
    submissions = []

    for subText in submissionsList:
        if subText.find("[") != -1 and subText.find("]") != -1 and subText.find("(") != -1 and subText.find(")") != -1:
            submission = []
            submission.append(str(subText[subText.find("[")+1:subText.find("]")]))
            submission.append(str(subText[subText.find("(")+1:subText.find(")")]))
            rightSide = subText[subText.find(")")+1:]
            submission.append(str(rightSide[rightSide.find("(")+1:rightSide.find(")")]))
            submissions.append(submission)

    return submissions

def getProjectResources(wiki):
    wikiPage = ""

    wikiPage = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md.encode("ascii", "ignore"), "load wiki page " + str(wiki) + " in getProjectResources()")

    signifier = "resource%20information/urls%20here%29))\r\n\r\n"
    marker = wikiPage.find(signifier)
    if marker == -1:
        return []
    else:
        marker += len(signifier)

    tempText = wikiPage[marker:]

    markerEnd = tempText.find("\r\n\r\n***")

    if markerEnd == -1:
        return []

    resourcesText = tempText[:markerEnd]

    resourcesList = resourcesText.split("\r\n\r\n")
    resources = []

    for recText in resourcesList:
        links = findLinks(recText)
        if links:
            resources.append(links[0])

    return resources

def getProjectQuestions(wiki):
    wikiPage = ""

    wikiPage = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in getProjectQuestions()")
    
    signifier = "question%20details%20here%29))\r\n\r\n"
    marker = wikiPage.find(signifier)
    if marker == -1:
        return []
    else:
        marker += len(signifier)

    tempText = wikiPage[marker:]

    markerEnd = tempText.find("\r\n\r\n***")

    if markerEnd == -1:
        return []

    questionsText = tempText[:markerEnd]

    questionsList = questionsText.split("\r\n\r\n")
    questions = []

    for quesText in questionsList:
        links = findLinks(quesText)
        if links:
            questions.append(links[0])

    return questions

def extractId(url):
    index = url.find("comments/") + len("comments/")
    return url[index:index+6]

def getWikiTitle(wiki):
    wikiPage = ""

    wikiPage = attempt(lambda: r.get_wiki_page(ludobots, wiki).content_md, "load wiki page " + str(wiki) + " in getWikiTitle()")

    signifier = "###"
    marker = wikiPage.find(signifier) + len(signifier)
    markerEnd = marker + wikiPage[marker:].find("\r\n")
    if marker == -1:
        return "Undefined Page Title"
    return wikiPage[marker:markerEnd]

def getHypotheses():
    data = ""

    data = attempt(lambda: r.get_wiki_page(ludobots, "hypothesis_data").content_md, "load wiki page hypothesis_data in getHypothesis()")
    lines = data.split("\r\n\r\n")
    hypotheses = []

    for line in lines:
        hypotheses.append(line[:line.find(":")])

    return hypotheses

def getWikiPageType(wiki):
    projects = ""

    projects = attempt(lambda: r.get_wiki_page(ludobots, "ludobots_projectdata").content_md.split(","), "load wiki page ludobots_projectdata in getWikiPageType()")
    hypotheses = getHypotheses()

    if wiki in projects:
        return "project"
    if wiki in hypotheses:
        return "hypothesis"
    return "unknown"

def updateLog(string):
    '''header = "###############################\n##  treeLudobot's Error Log  ##\n###############################\n\n"

    timestring = time.strftime("%m/%d/%Y %H:%M - ", time.gmtime())

    log = open("treeLudobot_log.txt", "r")
    logData = log.read()
    logData = logData.replace(header, "")
    log.close()

    log_w = open("treeLudobot_log.txt", "w")
    log_w.write(header+timestring+string+"\n"+logData)
    log_w.close()'''
    pass

#connect to reddit-necessary before scanning reddit or uploading the tree
def redditSetup():
    global r
    global ludobots
    
    print "Configured for Server Image Generation"

    r = attempt(lambda: praw.Reddit('/r/ludobots treeLudobot UVM'), "create reddit session")
    
    attempt(lambda: r.login("treeLudobot", "nikolatesla"), "log in as treeLudobot")
    
    ludobots = attempt(lambda: r.get_subreddit("ludobots"), "log in as treeLudobot")
    
    updateLog("Successful Run")

##################################################################################################################################################################

#global variables
global count
global labelRefs

G = nx.Graph()

PATH = os.path.expanduser("ludobotsTreeData.gpickle")

#helper functions-used to parse and edit the tree

#traverses the tree and updates the edge weights based on the size of the child node
def updateEdgeWeights(nodeId, parentId, seen):
    seen.append(nodeId)
    node = G.node[nodeId]
    for child in G.neighbors(nodeId):
        if child not in seen:
            updateEdgeWeights(child, nodeId, seen)
            #G.edge[nodeId][child]["weight"] = node["_size"]
            G.edge[nodeId][child]["weight"] = node["_size"]
            G.edge[nodeId][child]["width"] = node["_size"]
    return

#traverses the tree and changes every node's size based on how many successors it has
def getNumChildren(parentId, grandParentId, seen):
    seen.append(parentId)
    node = G.node[parentId]
    sum = 1
    colorDict = {"project": BLUE, "index": BLUE, "question": LIGHT_GREEN, "resource": DARK_GREEN, "submission": RED}
    weighted = ["project", "question", "resource", "index"]
    if node["_id"] in weighted:
        sum += 0
    # set the color
    G.node[parentId]["_color"] = colorDict.get(node["_id"], (1.0 ,1.0, 1.0))
    '''#relabel blanks
    if G.node[parentId]["label"] == "blank":
        G.node[parentId]["label"] = ""'''
    #print neighbors
    if node["label"] == 2:
        #pprint(G.neighbors(parentId))
        pass
    for child in G.neighbors(parentId):
        if child not in seen:
            sum += getNumChildren(child, parentId, seen)
    node["_size"] = sum
    if node["_id"] in weighted:
        node["_size"] += 400
    if sum > 1:
        #print str(sum) + " " + str(node["label"])
        pass
    return sum
    
#adds the submissions for a specified project
def addSubmissions(currentId, maxSubmissions, fullTraverse):
    submissions = getProjectSubmissions(currentId)
    
    if fullTraverse or maxSubmissions > len(submissions):
        maxSubmissions = len(submissions)
    
    for i in range(maxSubmissions):
        submission = submissions[i]
        G.add_node(submission[1], _id="submission", _size=300, label="")#RED
        #print "added submission node: " + str(submission)
        #labelDict[submission[1]] = ""
    
        #attempt(lambda: labelRefs.append([r.get_submission(submission_id=extractId(submission[1])).title, submission[1], "submission"]), "appending labelRefs for project submission in Parse_Forest()")
    
        G.add_edge(currentId, submission[1])

#adds resource and question nodes for a specified project
def addResourcesAndQuestions(currentId):
    resources = getProjectResources(currentId)
    questions = getProjectQuestions(currentId)
    
    subCount = 1
    for resource in resources:
        name = str(count - 1 + 1.0 * subCount / 100)
        G.add_node(resource, _id="resource", _size=300, label=name)#DARK_GREEN
        #labelDict[resource] = str(count - 1 + 1.0 * subCount / 100)
        subCount += 1
    
        #attempt(lambda: labelRefs.append([r.get_submission(submission_id=resource).title, resource, "resource", name]), "appending labelRefs for project resource in Parse_Forest()")
    
        #print "added resource node: " + str(resource)
        G.add_edge(currentId, resource)
    
    for question in questions:
        name = str(count - 1 + 1.0 * subCount / 100)
        G.add_node(question, _id="question", _size=300, label=name)#LIGHT_GREEN
        #labelDict[question] = str(count - 1 + 1.0 * subCount / 100)
        subCount += 1
    
        #attempt(lambda: labelRefs.append([r.get_submission(submission_id=question).title, question, "question", name]), "appending labelRefs for project question in Parse_Forest()")
    
        #print "added question node: " + str(question)
        G.add_edge(currentId, question)

#parses the wiki page to generate the tree
def Parse_Forest(parentId, currentId, fullTraverse=True, maxNodes=5, maxSubmissions=5):
    global count, labelRefs

    type = getWikiPageType(currentId)
    
    branches = getWikiRefsTo(currentId)
    
    if type == "project":
        #add project node
        print "added project node: " + str(currentId)
        G.add_node(currentId, _id="project", _size=300, label=count)#BLUE
        #labelDict[currentId] = count
        
        labelRefs.append(["[PROJECT] " + getWikiTitle(currentId), "http://www.reddit.com/r/ludobots/wiki/" + str(currentId), "project", count])
        count += 1
        G.add_edge(parentId, currentId)
        
        #add lower level nodes
        addSubmissions(currentId, maxSubmissions, fullTraverse)
        addResourcesAndQuestions(currentId)
        
    elif type == "hypothesis":
        #add hypothesis node
        G.add_node(currentId, _id="hypothesis", _size=700, _color=(1.0, 1.0, 1.0), label=count)
        #labelDict[currentId] = count
        
        labelRefs.append(["[HYPOTHESIS] " + getWikiTitle(currentId), "http://www.reddit.com/r/ludobots/wiki/" + str(currentId), "hypothesis", count])
        count += 1
        G.add_edge(parentId, currentId)
        
        #add lower level nodes
        addResourcesAndQuestions(currentId)

    else:
        print "Error: The post with id " + currentId + " is of the unrecognized type " + type + "."
    
    #loop through branches
    if fullTraverse or count < maxNodes:
        #pprint(currentId)
        for branch in branches:
            Parse_Forest(currentId, branch, fullTraverse=fullTraverse, maxNodes=maxNodes, maxSubmissions=maxSubmissions)

#unused-scales a set of data to fit within a range-could be used for node size adjustments
def scaleTo(list, actualMin, actualMax):
    maximum = max(list)
    minimum = min(list)
    ranger = maximum - minimum
    actualRange = actualMax - actualMin
    scaleFactor = 1.0 * ranger / actualRange
    
    output = [(listItem - minimum) / scaleFactor + actualMin for listItem in list]
    '''for i in range(len(list)):
        if list[i] > 1:
            print str(list[i]) + " " + str(output[i])'''
    return output

#node size refers to the area of the node-to work in radii, this function was necessary
def radToArea(rad):
    return math.pi * math.pow(rad, 2)
    
#primary functions

#requires redditSetup to be run first, gathers data from reddit to build the tree
def scanReddit(fullTraverse=True, maxNodes=5, maxSubmissions=5):
    global count, labelRefs
    count = 1
    labelRefs = []

    G.add_node("index", _id="index", _size=300, label=count)#BLUE
    #labelDict["index"] = count
    
    labelRefs.append(["Welcome Page", "http://www.reddit.com/r/ludobots/wiki/index", "welcome", count])
    count += 1
    Parse_Forest("index", "core00", fullTraverse=fullTraverse, maxNodes=maxNodes, maxSubmissions=maxSubmissions)
    Parse_Forest("index", "2h5f5a")

#loads the tree from a saved file
def loadTree():
    global G
    G = nx.read_gpickle(PATH)

#saves the tree to a file
def saveTree():
    nx.write_gpickle(G, PATH)

#formats the raw tree data by adding edge weights and node sizes
def formatTree():
    '''prioritized = {}
    for anode in G.nodes():
        if G.node[anode]["_id"] != "submission":
            prioritized[anode] = G.node[anode]
            
            G.remove_node(anode)
    pprint(prioritized)
    G.add_nodes_from(prioritized)
    gtest = nx.Graph()
    gtest.add_nodes_from(prioritized)
    #pprint(G.node)
    for key in prioritized:
        a = key
        for key in prioritized[key]:
            b = key
            G.node[a][b] = prioritized[a][b]'''

    getNumChildren("index", None, ["index"])
    
    updateEdgeWeights("index", None, ["index"])

    
#prepares the tree and creates an image of it
def drawTree():
    #create the backbone (all nodes that are not submissions)
    G_Backbone = copy.deepcopy(G)
    for anode in G_Backbone.nodes():
        if G.node[anode]["_id"] == "submission":
            G_Backbone.remove_node(anode)   

    pos_backbone = nx.graphviz_layout(G_Backbone, prog='neato', args='-Goverlap=prism')
    
    #calculates node positions for the full tree, backbone and submissions
    posCalc = nx.spring_layout(G, pos=pos_backbone, fixed=G_Backbone.node, k=submissionDispersion)
    

    plt.figure(figsize=(10, 14))

    nodes = G.nodes()
    
    main = ["project", "hypothesis"]
    
    #get n1 (min number of children) and n2 (max number of children)
    n1 = float('inf')
    n2 = 0
    for anode in nodes:
        if G.node[anode]["_id"] in main:
            curSize = len(G.neighbors(anode))
            if curSize < n1:
                n1 = curSize
            if curSize > n2:
                n2 = curSize
                
    #find equation of a line relating number of children (x-axis) to output node size (y-axis)
    r1 = minProjectRadius
    r2 = maxProjectRadius
    
    m = 1.0 * (r2 - r1) / (n2 - n1)
    b = 1.0 * r1 - m * n1

    #set sizes     
    for anode in nodes:
        other = ["resource", "question"]
        if G.node[anode]["_id"] == "submission":
            G.node[anode]["_size"] = radToArea(submissionRadius)
        elif G.node[anode]["_id"] in other:
            G.node[anode]["_size"] = radToArea(qrSize)
        elif G.node[anode]["_id"] in main:
            #G.node[anode]["_size"] = radToArea(15 + 1 * math.log(len(G.neighbors(anode)), 2))
            #rad = minProjectRadius + 1.0 * len(G.neighbors(anode)) / 5
            n = len(G.neighbors(anode))
            rad = m * n + b
            G.node[anode]["_size"] = radToArea(rad)
    
    
    #set index size
    G.node["index"]["_size"] = radToArea(r2)
    G.node["index"]["_color"] = PURPLE
    
    #create separate variables for colors, sizes, and edges
    colors = [G.node[anode]['_color'] for anode in nodes]
    sizes = [G.node[anode]["_size"] for anode in nodes]  
    edges = G.edges()
    
    widths = [G.edge[anedge]["width"] for anedge in edges if anedge in G.edge]
    
    #labels for nodes
    labelDict = {}
    for anode in G.node:
        labelDict[anode] = G.node[anode]["label"]

    #draw the tree initially
    nx.draw(G, posCalc, node_size=sizes, alpha=1, nodelist=nodes, node_color=colors, with_labels=True, labels=labelDict, font_size=8)#width=widths
   
    #redraw the backbone of the tree to force the submission nodes to be underneath the backbone
    subPosCalc = {}
    
    subSizes = [G.node[anode]["_size"] for anode in G.nodes() if G.node[anode]["_id"] != "submission"]
    subNodes = [anode for anode in G.nodes() if G.node[anode]["_id"] != "submission"]
    subLabelDict = {}
    for anode in subNodes:
        subPosCalc[anode] = posCalc[anode]
        subLabelDict[anode] = labelDict[anode]
    subColors = [G.node[anode]["_color"] for anode in G.nodes() if G.node[anode]["_id"] != "submission"]
    subEdges = [anedge for anedge in edges if (G.node[anedge[0]]["_id"] != "submission" and G.node[anedge[1]]["_id"] != "submission")]

    nx.draw(G, subPosCalc, node_size=subSizes, alpha=1, nodelist=subNodes, node_color=subColors, with_labels=True, labels=subLabelDict, font_size=8, edgelist=subEdges)
    
    #save the image file
    plt.savefig(os.path.expanduser("ludobotsTree.png"), transparent=True)
    
#uploads the tree and associated data to the reddit wiki page
def uploadTree():
    global labelRefs
    print "uploading to reddit..."

    attempt(lambda: r.delete_image(ludobots, "ludobotsTree"), "delete image ludobotsTree in updateTree()")

    attempt(lambda: r.upload_image(ludobots, os.path.expanduser("ludobotsTree.png"), "ludobotsTree"), "upload image ludobotsTree.png in updateTree()")

    r.config.decode_html_entities = True

    print "updating reddit tree images..."

    attempt(lambda: r.set_stylesheet(ludobots, r.get_stylesheet(ludobots)['stylesheet']), "updating stylesheet so as to update images site-wide for ludobotsTree.png in updateTree()")

    print "updating tree wiki page..."

    treeWiki = "#The Ludobots Tree\r\n\r\n[](/ludobotstreekey)\r\n\r\n[](/r/ludobots/wiki/tree)\r\n\r\n***\r\n\r\n###Tree References\r\n\r\n"

    for i in range(0, len(labelRefs)):
        authorText = ""
        if labelRefs[i][2] == "project" or labelRefs[i][2] == "hypothesis":
            treeWiki += "***\r\n\r\n"
            bold = "**"
        elif labelRefs[i][2] == "welcome":
            treeWiki += ""
            bold = "**"
        else:
            author = str(r.get_submission(url=labelRefs[i][1]).author)
            authorText = " (**[" + author + "](http://www.reddit.com/r/ludobots/wiki/" + author + ")**)"
            treeWiki += "* "
            bold = ""

        treeWiki += str(labelRefs[i][3]) + "\\. " + bold + "[" + labelRefs[i][0] + "](" + labelRefs[i][1] + ")" + bold + authorText
        treeWiki += "\r\n\r\n"

    attempt(lambda: r.edit_wiki_page(ludobots, "tree", treeWiki), "upload wiki page tree in updateTree()")
        
#function calls
redditSetup()
scanReddit()
saveTree()
loadTree()
formatTree()
drawTree()
uploadTree()