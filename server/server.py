#!/usr/bin/env python3
import sys
import os
import asyncio
import testprotocol_pb2
import websockets
import html
import socket
import ssl
import logging

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("server")
logger.setLevel("DEBUG")

class variables:
    hostname = "127.0.0.1"
    port = 5678
    ssl_context = None

def loadConfig(config):
    try:
        with open(config, "r") as f:
            conf = variables()
            llist = [line.rstrip() for line in f]
            conf.hostname = llist[0]
            conf.port = llist[1]
            if not llist[2].startswith('#') and not llist[3].startswith('#'):
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(llist[2], llist[3])
                conf.ssl_context = ssl_context
            return conf
    except Exception as e:
        print(e)

class User: #user class on vain huoneen sisällä
    ID = 0 #uniikki tunniste
    username = "testi"
    
    def addwebsocket(): #liittää websocketin käyttäjään
        pass

class Room:
    """
    huone johon voi liittyä ja jossa olevien viestit (location, chattiviestit jne...)
    välitetään toisille
    """
    members = {} #huoneen jäsenet eli user classit
    teams = {#joukkuelista
        "default": "unassigned" #luodaan oletusjoukkue
    }
    admins = {} #adminit
    user = User()
    clients = {}
    count = 0
    def counter(self):
        """
        counteri, jotta kaikilla on uniqueid
        """
        self.count += 1
        return self.count

    async def sendmessage(self, websocket, msg):
        """
        lähettää viestin kaikille huoneessa oleville
        """
        if self.clients:
            await asyncio.wait([client.send(msg) for client in self.clients]) #if client != websocket])

    async def handlemessage(self, websocket, msg, msgout):
        """
        parsee viestit ja muodostaa viestin
        msgout parametri varmaan poistettavissa, jos ei löydy
        käyttötarkoitusta, jossa servu injectaisi viestiin jotain
        """
        if msg.chatmsg:
            serverchatmsg = testprotocol_pb2.Chatmessage()
            serverchatmsg.senderID = self.clients[websocket]
            serverchatmsg.msg = html.escape(msg.chatmsg)
            msgout.chatmsg.append(serverchatmsg)

        if msg.HasField("location"):
            loc = msg.location
            loc.senderID = self.clients[websocket]
            msgout.locations.append(loc)
            
        if msg.HasField("shape"):
            shape = msg.shape
            shape.senderID = self.clients[websocket]
            msgout.shapes.append(shape)

        bytes = msgout.SerializeToString()
        await self.sendmessage(websocket, bytes)

    def createuser(self, websocket):
        """
        lisää käyttäjän huoneeseen
        todo(?): ota parametrinä msg, jossa on position, nimi jne
        ja ilmoita se muille(?)
        """
        self.members[userID] = user #luo käyttäjän, avain on käyttäjän uniikki ID
        
    def adduser(self, websocket):
        self.clients[websocket] = self.counter()
    
    def removeuser(self, websocket):
        """
        poistaa käyttäjän huoneesta
        """
        del self.clients[websocket]
        #del self.members[userID]
    
    def setpassword(self, websocket):#asettaa huoneelle salasanan
        pass
        #miten salasana tallennetaan? missä muodossa? mihin?
    
    def Addmin(self, websocket): #asettaa käyttäjän adminiksi
        pass
    
    def removeadmin():#poista admin oikeudet
        pass
    
###TODO: joku luokka, joka handlaa servun kaikki huoneet
###ja pitää huolta oikeuksista jne
class RoomHandler:
    clients = {}
    room = Room()
    async def messagehandler(self, websocket, msg, answer): #välittää vietit huoneille
        await self.room.handlemessage(websocket, msg, answer)
    
    def handlemessage(self, websocket, msg):  #käsittelee huoneiden hallintaa koskevat viestit
        if msg.roomname:    #jos roomname kenttä on olemassa
            joinroommsg = testprotocol_pb2.JoinRoom()
            if msg.createroom == true:  #jos createroom checkbox on merkittynä
                newroom()   #luo uusi huone syötetyillä parametreillä
            else:
                handlelogin()#yritä liittyä olemassaolevaan huoneeseen
                
        
    rooms = {}#dict jossa huoneet olioina, huoneen nimi on avain
    
    def newroom(self, websocket, msg):#luo uuden huoneen
        if msg.roomname in self.rooms:#tarkistaa jos samanniminen huone on jo olemassa
            pass #virheilmoitus käyttäjälle
        else:
            self.rooms[msg.roomname] = room #luodaan uusi huone
            handleadduser() #lisätään käyttäjä luotuun huoneeseen
        
    def removeroom(self, msg):#poistaa olemassa olevan huoneen
        del self.rooms[msg.roomname]#sulkuihin poistettavan huoneen nimi
        
    def handlelogin(self, websocket): #yhdistäminen palvelimelle
        self.room.adduser(websocket)
        #self.clients[websocket] = self.counter()
    
    def handlelogout(self, websocket): #yhteyden katkaisu palvelimelta
        self.room.removeuser(websocket)
        #del self.clients[websocket]
        
    def handleadduser(self, websocket, msg): #lisää käyttäjän tiettyyn huoneeseen
        self.rooms[msg.roomname].createuser(websocket)
        
    def handleremoveuser(self, websocket, msg): #poistaa käyttäjän tietystä huoneesta
        self.rooms[msg.roomname].removeuser(websocket)
        
    #joku metodi jolla luodaan uniikit ID:t käyttäjille
        
roomhandler = RoomHandler()
    

async def serv(websocket, path):
    logger.info("%s connected", websocket.remote_address)
    roomhandler.handlelogin(websocket)
    try:
        async for message in websocket:		#palvelimen juttelu clientin kanssa
            answer = testprotocol_pb2.FromServer()
            msg = testprotocol_pb2.ToServer()
            msg.ParseFromString(message)	#clientiltä tullut viesti parsetaan auki
            logger.debug(msg);
            await roomhandler.messagehandler(websocket, msg, answer)
    except Exception as e:
        print(e)
    finally:
        roomhandler.handlelogout(websocket)



def runServer(config):
    logger.info("Starting server... " + config.hostname +":" + config.port)
    logger.info("ssl enabled: " + str(config.ssl_context is not None))
    start_server = websockets.serve(serv, config.hostname, config.port, ssl=config.ssl_context)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    config = loadConfig("server.config")
    runServer(config)

