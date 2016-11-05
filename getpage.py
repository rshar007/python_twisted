from twisted.web.client import getPage
from twisted.internet import reactor
import json

url = "https://maps.googleapis.com/maps/api/place/" \
      "nearbysearch/json?location=-33.8670522,151.1957362" \
      "&radius=500&type=restaurant&name=cruise&key=" \
      "AIzaSyAI7i4FJB5-_Vysqrq1vMoEQQuXODXuXLM"

def stop(result):
    reactor.stop()

def printPage(result):
    print "*" * 80
    jdata = json.loads(result)
    results = jdata["results"]
    jdata["results"] = results[0:1]
    #print "%s" % json.dumps(jdata, indent=4)
    print "%s" % json.dumps(jdata, indent=4)

    
d = getPage(url)
d.addCallbacks(printPage)
d.addCallback(stop)

reactor.run()
