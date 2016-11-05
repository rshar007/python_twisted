from twisted.internet import reactor, protocol

class AtClient( protocol.Protocol ):
    def connectionMade( self ):
        str = "IAMAT kiwi.cs.ucla.edu " \
              "+34.068930-118.445127 1400794645.392014450"
        self.transport.write( str )
    def dataReceived( self, data ):
        print "Server said:", data
        self.transport.loseConnection()

class AtClientFactory( protocol.ClientFactory ):
    def buildProtocol( self, addr ):
        return AtClient()

    def clientConnectionFailed( self, connector, reason ):
        print "Connection failed."

    def clientConnectionLost( self, connector, reason ):
        print "Connection lost."
    
def main():
    server_port_dict = { "Alford":   44444,
                         "Bolden":   44445,
                         "Hamilton": 44446,
                         "Parker":   44447,
                         "Welsh":    44448 }
    
    reactor.connectTCP( "localhost",
                       server_port_dict[ "Parker" ],
                       AtClientFactory() )
    reactor.run()

if __name__ == "__main__": main()
