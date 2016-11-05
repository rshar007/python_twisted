from twisted.internet import reactor, protocol
from twisted.web.client import getPage
from twisted.internet.defer import Deferred
from twisted.python import log
import sys, re, json
from time import time, asctime

# server address
server_addr = "localhost"

# Google Places API key
from myconfig import *

# Byte-compiled regular expression for GPS coordinates
r = re.compile("([\+|-]\d+\.\d+)([\+|-]\d+\.\d+)")

# Server names and their ports
server_names = { "Alford"   : 44444,
                 "Bolden"   : 44445,
                 "Hamilton" : 44446,
                 "Parker"   : 44447,
                 "Welsh"    : 44448 }

# Server friends, i.e., servers that talk to each other
friendly_servers = { "Alford"  : [ "Parker", "Welsh" ],
                     "Bolden"  : [ "Parker", "Welsh" ],
                     "Hamilton": [ "Parker" ],
                     "Parker"  : [ "Alford", "Bolden", "Hamilton" ],
                     "Welsh"   : [ "Alford", "Bolden" ] }

# Client dictionary
servers = {}

class AtServer( protocol.Protocol ):
    def __init__( self ):
        self.name = sys.argv[1]

        # server log file
        log.startLogging(open('./server_logs/%s' % self.name, 'w'))
        
        log.msg("%(server_name)s started at %(asctime)s" % {
            "server_name": self.name,
            "asctime": asctime() })
        
    def dataReceived( self, data ):
        d = Deferred()
        d.addCallback( self.handleInput )
        d.callback( data )
        log.msg("received data to process")

    def handleInput(self, data):
        # process the data received
        types = [ str, str, str, str, str, str ]
        input = [ ty(val) for ty, val in
                  zip( types, data.split(" ")) ]
        # figure out the command
        command = input[0]
        
        if ( command == "IAMAT" ):
            dIAMAT = Deferred()
            dIAMAT.addCallback(self.handleIAMAT)
            dIAMAT.callback(input)
            log.msg("IAMAT response")

        elif ( command == "WHATSAT" ):
            dWHATSAT = Deferred()
            dWHATSAT.addCallback(self.handleWHATSAT)
            dWHATSAT.addErrback(self.noentry)
            dWHATSAT.callback(input)
            log.msg("WHATSAT response")

        elif ( command == "AT"):
            self.handleAT(input)
            dAT = Deferred()
            dAT.addCallback(self.handleAT)
            dAT.addErrback(self.noentry)
            dAT.callback(input)
            log.msg("AT response")

        else:
            self.transport.write( "?" )
            log.msg("received invalid command")

    def storeServerLocation(self,
                            server_name,
                            time_diff,
                            client,
                            location,
                            interaction_time):
        '''Store a server's location.
        
        arguments:
        server_name = server that originally handled the request
        time_diff   = server-client time difference
        client      = client name
        location    = location string provided by the client
        interaction = time of original interaction

        stores:
        all the arguments in a server dictionary
        '''

        # parse the GPS location
        m = r.match(location)
        latitude = float(m.group(1))
        longitude = float(m.group(2))

        servers[client] = {
            "server-name"     : server_name,
            "time-difference" : time_diff,
            "client-name"     : client,
            "location"        : location,
            "sc-time"         : interaction_time,
            "latitude"        : latitude,
            "longitude"       : longitude }
        log.msg("stored information about %s"
                % client)
            
    def handleIAMAT(self, input):
        server_name = self.name
        client_name = input[1]
        location    = input[2]

        client_time = input[3]
        server_time = time()
        time_diff = self.calculate_time_difference(
            client_time, server_time)

        self.storeServerLocation( server_name,
                                  time_diff,
                                  client_name,
                                  location,
                                  server_time )
        
        output_str = "AT %s %s %s %s %s" % ( server_name,
                                               time_diff,
                                               client_name,
                                               location,
                                               server_time )

        self.transport.write( "%s\n" % output_str )
        self.propogateAT(output_str)

    def handleAT(self, input):
        server_name      = input[1]
        time_diff        = input[2]
        client_name      = input[3]
        location         = input[4]
        interaction_time = input[5]

        self.storeServerLocation( server_name,
                                  time_diff,
                                  client_name,
                                  location,
                                  interaction_time )
        
        output_str = "AT %s %s %s %s %s" % ( server_name,
                                             time_diff,
                                             client_name,
                                             location,
                                             time_diff )

    def handleWHATSAT(self, input):
        '''input will be a list of values:
        input[0] = WHATSAT command
        input[1] = client name
        input[2] = information upper bound
        input[3] = radius of the client
        AT <server> <time difference> <client> <location>...
        <time of server-client interaction> <GOOGLE info>
        '''
        client = input[1]
        radius = input[2]
        upperbound = int(input[3])
        
        lookup = servers[client]
        
        self.transport.write(
            "AT %s %s %s %s %s\n" % (
                lookup["server-name"],
                lookup["time-difference"],
                lookup["client-name"],
                lookup["location"],
                lookup["sc-time"] ))

        self.retrievePlacesJSON( client, radius, upperbound)

    def calculate_time_difference(self, t1, t2):
        time_diff = str(float(t2) - float(t1))
        if (float(time_diff) >= 0):
            time_diff = "+" + time_diff

        return time_diff

    def retrievePlacesJSON(self, client, radius, n):
        '''
        input includes three parameters:
        client - client server to lookup
        radius - desired radius to search in km
        n - number of desired results
        '''
        print "client %s radius %s n %s\n" % (client, radius, n)
        key = google_key
        lat = servers[client]["latitude"]
        long = servers[client]["longitude"]
        r_in_kilometers = int( radius ) * 1000
        base_url = "https://maps.googleapis.com/maps/api/place/" \
                   "nearbysearch/json?"
        
        request_url = "%(base_url)slocation=%(lat)s,%(long)s" \
                      "&radius=%(r)i&key=%(key)s" % { 'base_url': base_url,
                                                    'lat': lat,
                                                    'long': long,
                                                    'r': r_in_kilometers,
                                                    'key': key }
        g = getPage(request_url)
        g.addCallback(self.writeoutJSON, n)
        g.addErrback(self.errorRetrievingData)
        log.msg("retrived data for the user")

    def errorRetrievingData(self, failure):
        self.transport.write("Couldn't retrieve JSON data. :c\n")
        log.msg("Could not retreive JSON data")

    def noentry(self, failure):
        self.transport.write("no such entry. :c\n")
        log.msg("could not find entry requested")

    def couldNotConnectFriend(self, failure):
        print "Could not connect to my friend: %s" % failure
        log.msg("Could not connecto to friend server: %s" % failure)
        
    def writeoutJSON(self, result, n):
        jdata = json.loads(result)
        results = jdata["results"]
        jdata["results"] = results[:n]
        self.transport.write( "%s\n" % json.dumps(jdata, indent=4))
        
    def speakName( self, data ):
        self.transport.write(
            "This is %s, hello.\n" % data )

    def propogateAT( self, message ):
        name = self.name
        for friend in friendly_servers[ name ]:
            reactor.connectTCP( server_addr,
                                server_names[friend],
                                friendClientFactory( message ))
        log.msg("propogating AT information to other servers")

class AtServerFactory( protocol.Factory ):
    def buildProtocol( self, addr ):
        return AtServer()

class friendClient(protocol.Protocol):
    def __init__(self, message):
        self.message = message
        
    def connectionMade(self):
        self.transport.write(self.message)
        self.transport.loseConnection()
        log.msg("sucessfully connected to friend server")

class friendClientFactory(protocol.ClientFactory):
    def __init__( self, message ):
        self.message = message
    
    def buildProtocol( self, addr ):
        return friendClient( self.message )

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed. :c\n"
        log.msg("Could not connect to friend server")

    def clientConnectionLost(self, connector, reason):
        log.msg("disconnected from friend server")
    
def check_server_name():
    
    if len( sys.argv ) != 2:
        raise ValueError(
            "Usage: python server.py <server name>")
    else:
        name = sys.argv[ 1 ]
        if not name in server_names:
            raise ValueError(
                "%s is not a valid server name" % name )
        return server_names[ name ]

def main():
    server_port = check_server_name()
    reactor.listenTCP( server_port, AtServerFactory() )
    
    reactor.run()
    
if __name__ == "__main__": main()
