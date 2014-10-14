##
## WSManta
##
##  Levantar un servidor Autobahn y comunicar por serial mediante Twisted
##
##  Recepción de los valores de cada sensor, de una matriz de sensores 
##  de tamaño variable, por serial, enviados por una microcontroladora (Arduino)
##
##  Procesamiento de la información, dependiendo del estado, 
##  para permitir el calibrado del sistema a maximos y a mínimos. 
##  Procesar los datos calibrados, raw, con o sin buffer y limpieza de la señal.
##
##  Gestión de la comunicación entre el cliente y la placa microcontroladora,
##  para el envío de matrices de datos al cliente y comunicar los cambios de estado a la placa. 

import sys
import time

if sys.platform == 'win32':
   ## on windows, we need to use the following reactor for serial support
   ## http://twistedmatrix.com/trac/ticket/3802
   ##
   from twisted.internet import win32eventreactor
   win32eventreactor.install()

from twisted.internet import reactor
print "Using Twisted reactor", reactor.__class__
print

from twisted.python import usage, log
from twisted.protocols.basic import LineReceiver
from twisted.internet.serialport import SerialPort
from twisted.web.server import Site
from twisted.web.static import File

from autobahn.twisted.websocket import listenWS

from autobahn.wamp1.protocol import WampServerFactory, \
                                    WampServerProtocol, \
                                    exportRpc



class Serial2WsOptions(usage.Options):
   
   optFlags = [
      ['debugserial', 'd', 'Turn on Serial data logging.'],
      ['debugwamp', 't', 'Turn on WAMP traffic logging.'],
      ['debugws', 'r', 'Turn on WebSocket traffic logging.']
   ]

   optParameters = [
      ['baudrate', 'b', 57600, 'Serial baudrate'],
      ['port', 'p', 3, 'Serial port to use (e.g. 3 for a COM port on Windows, /dev/ttyATH0 for Arduino Yun, /dev/ttyACM0 for Serial-over-USB on RaspberryPi'],
      ['webport', 'w', 8080, 'Web port to use for embedded Web server'],
      ['wsurl', 's', "ws://localhost:9000", 'WebSocket port to use for embedded WebSocket server']
   ]


## MCU protocol
##  Recibir los datos del serial 
##  Procesado de datos en función del estado
##  Gestionar la comunicación entre el microcontrolador y el cliente
class McuProtocol(LineReceiver):

   ## Definimos las propiedades de las matrices para la Malla actual
   matrizMinimos = []
   matrizMaximos = []
   matrizEscaneando = []
   dimension1 = 16
   dimension2 = 16
   
   
   ##Definimos las propiedades del Buffer de datos
   matrizBuffer = []
   bufferSize = 4
   bufferPos = 0
   lecturaResistencia = True
   buffering = False

   ##Variables de estado y control de datos
   estado = "Minimos"   
   count = -1
   eventos = 0
   tiempoAnterior = 0
   minVal = 0
   maxVal = 0
   
   ##Tipos lectura: 1)Resistencia / 2) Condensador
   tipoLectura = 1
 
   ##Inicializamos las matrices de datos 
   def inicializa(self):		
        
     ## Definimos las dimensiones de la MatrizMinimos, para calibrar
     self.matrizMinimos = [[self.minVal for j in range (self.dimension1)] for i in range (self.dimension2)]

     ## Definimos las dimensiones de la matrizMaximos, para calibrar
     self.matrizMaximos = [[self.maxVal for j in range (self.dimension1)] for i in range (self.dimension2)]

     ## Definimos las dimensiones de la matrizEscaneando, para row data
     self.matrizEscaneando = [[0 for j in range (self.dimension1)] for i in range (self.dimension2)]
     
     ## Definimos las dimensiones de la matrizBuffer, para buffering de datos
     self.matrizBuffer = [[[0 for j in range(self.bufferSize)] for i in range(self.dimension2)] for k in range(self.dimension1)]
     
     ## Inicializamos el contador de tiempo
     self.tiempoAnterior = time.time()
	

   ##Construimos la clase principal e inicializamos las matrices. 
   ##
   def __init__(self, wsMcuFactory):
      self.wsMcuFactory = wsMcuFactory
      self.inicializa()            
   
      
   ## Exportamos el metodo 'enviar' como RPC para que pueda ser llamado desde el cliete
   ## Manejo del microcontrolador desde el panel de control del cliente.
   @exportRpc("enviar")
   def enviar(self, valores):
     ##Enviamos el nuevo valor del delay al microcontrolador
     if (int(valores[0]) > 0):
        self.transport.write(str(valores[0]))
        self.transport.write("d")     
        if self.wsMcuFactory.debugSerial:
           print "Nuevo valor del Delay(Micro):", valores[0]
           
     ##Enviamos valor de la resistencia variable al microcontrolador  
     if ( int(valores[1]) > 0):  
        self.transport.write(str(valores[1]))
        self.transport.write("r") 
        if self.wsMcuFactory.debugSerial:
           print "Valor de la resistencia variable(en construccion):", valores[1]

     ##Enviamos tipo lectura: 1)Resistencia / 2) Condensador    
     if ( int(valores[2]) > 0):  
       self.tipoLectura = valores[2]; 
       if (self.tipoLectura == 1):
           if self.wsMcuFactory.debugSerial:
              print "Tipo de lectura: Por Resistencia"
           self.lecturaResistencia = True 
           self.transport.write("r")  
       elif (self.tipoLectura == 2):
           if self.wsMcuFactory.debugSerial:
              print "Tipo de lectura: Por Condensador"
           self.lecturaResistencia = False 
           self.transport.write("c")   

   
   
   ## Exportamos el Metodo como RPC para que pueda ser llamado desde el cliete
   ##
   @exportRpc("control")
   def control(self, status):

      ##Recibimos del cliente el estado actual de calibrado/ raw. 
      ##Cargar, guardar y resetear los datos de la matriz actual
      if status == 0:
         self.estado = "Minimos"
      elif status == 1:
         self.estado = "Maximos"
      elif status == 2:
         self.estado = "Raw"
      elif status == 3:
         self.estado = "Calibrado"  
      elif status == 4:
	       self.estado = "Test"                
      elif status == 5:
         self.guardarMatriz()          
      elif status == 6:
	       self.cargarMatriz()
      elif status == 7:
	       self.resetMatriz()
      elif status == 8:
	       self.buffering = not self.buffering 
	       
      //Debug del estado actual
      if self.wsMcuFactory.debugSerial:
          print "Estado: ", self.estado
          
   ##Recibimos el valor, en 'line', que llega por serial desde arduino
   def lineReceived(self, line):

      //Debug del valor recibido
      if self.wsMcuFactory.debugSerial and not self.lecturaResistencia:
         print "Serial RX:", line
    
      ##Contador de llegada de datos
      self.count = self.count + 1

      try:               
 	       ##Obtenemos la fila y la columna de la matriz a a partir de la posicion del valor actual.
         row = int(round(self.count % 16))
         col = int(round(self.count / 16))

         ## Recibimos el dato del serial
         ##
         data = int(line)
  
         ## AL final de cada bloque (-1)
         ## ENVIAMOS MATRIZ COMPLETA
         if data == -1:    
             ##El contador de posicion de la matriz se reinicia
             self.count = -1
             ##El contador de Buffer se incrementa o reinicia
             if self.bufferPos >= self.bufferSize-1:
                self.bufferPos = 0
             else:
                if self.estado == "Calibrado" and self.buffering:
                    self.bufferPos = self.bufferPos + 1
             if self.estado == "Minimos":        
                 evt =  self.matrizMinimos
             elif self.estado == "Maximos":
                 evt = self.matrizMaximos
             elif self.estado == "Raw" or self.estado == "Test" or self.estado == "Calibrado":
                 evt = self.matrizEscaneando                     
             ##ENVIANDO MATRIZ
             self.wsMcuFactory.dispatch("http://example.com/mcu#analog-value", evt)
             self.eventos = self.eventos + 1                   
                    
                    
         ##Control de perdida del carater de control
         if self.count >= 255:
             self.count = -1
             
         ##Debug por pantalla de la velocidad de llegada de datos
         ##if self.wsMcuFactory.debugSerial:
         ##    if (time.time() - self.tiempoAnterior) > 1 :
	       ##	self.tiempoAnterior = time.time()
	       ##	print "Eventos/s: ", self.eventos
	       ##	self.eventos = 0

         
 	       ##[MINIMOS]: si el dato que llega es menor al anterior 
         ##lo guardamos en matrixMinimos 
         if self.estado == "Minimos" and data != -1:            
	         if self.matrizMinimos[row][col] == self.minVal or data > self.matrizMinimos[row][col] :
	 	         self.matrizMinimos[row][col] = data
       	
         ##[MAXIMOS]: si el dato que llega es mayor al anterior 
         ##lo guardamos en matrixMaximos 
         elif self.estado == "Maximos" and data != -1 :
            if data > self.matrizMaximos[row][col] :
	 	           self.matrizMaximos[row][col] = data
 
         ##[RAW]:Guardamos el dato en matrixEscaneando sin Mapear
         elif self.estado == "Raw" and data != -1 :
             self.matrizEscaneando[row][col] = data                       
             
         ##[CALIBRADO]:Guardamos el dato en matrixEscaneando ya Mapeado
         elif self.estado == "Calibrado" and data != -1 :
            divisor = (self.matrizMaximos[row][col] - self.matrizMinimos[row][col]) 
            if divisor == 0:
		            data = 0
            else :
              if (data < self.matrizMinimos[row][col]):
               		data = self.matrizMinimos[row][col]
              if (data > self.matrizMaximos[row][col]):
		              data = self.matrizMaximos[row][col]   
              ##Mapeamos el valor sobre 1024 y lo guardamos en matrizEscaneando                
              self.matrizEscaneando[row][col] = int (((data - self.matrizMinimos[row][col]) * 1024) / divisor)                         
              if self.buffering :
                self.matrizBuffer[row][col][self.bufferPos] = self.matrizEscaneando[row][col]
                self.limpiaDatos(row,col)
              
	       ##[TEST]: Muestra los colores de la escala
         elif self.estado == "Test":
              self.matrizEscaneando[row][col] = self.count * (1024/256)
      except ValueError:
         log.err('Unable to parse value %s' % line)
         print "Unable to parse value: ", line

   ##Analizamos los valores del buffer y limpiamos los datos o no...
   def limpiaDatos (self, row, col):      
      ##Solo se lleva a cabo la limpieza si entra un valor por encima del minimo
      if self.matrizEscaneando[row][col] > self.matrizMinimos[row][col]:
        posAnt = [0 for x in range(self.bufferSize)]
        for x in range(self.bufferSize):
            if x == 0:
              posAnt[x] = self.bufferPos
            elif posAnt[x-1] == 0:
              posAnt[x] = self.bufferSize-1
            else: 
              posAnt[x] = posAnt[x-1]-1
        
        ##Miramos las 3 posiciones anteriores.
        constanciaSenal = 3
        for x in range(constanciaSenal):
            ##Una opcion: if self.matrizBuffer[row][col][posAnt[x]] <= self.matrizMinimos[row][col] :
            #Otra:
            #  Eliminamos los valores inferiores al factor de incremento de señal definido
            if self.matrizBuffer[row][col][posAnt[x]] <= (self.matrizEscaneando[row][col]/constanciaSenal):                
                self.matrizEscaneando[row][col] = 0
                break
                
                
 
      ##Si el valores anteriores son muy bajos, no se muestra el valor actual
      ##Esto obliga a que la presion se mantenga como minimo durante 'constanciaSenal' lecturas
      ##o el valor sera considerado una interferencia y no sera mostrado  


   ##Sobreescritura del fichero de datos con la MatrizMaximos o MatrizMinimos actual
   def guardarMatriz(self):
      ##[MINIMOS]
      if self.estado == "Minimos":
        if self.wsMcuFactory.debugSerial:        
        	   print "Guardando Matriz Minimos" + '\n' + str(self.matrizMinimos)
    
        f = open("matrizMin.dat","w")
        f.write(str(self.matrizMinimos))
        
        f.close
      ##[MAXIMOS]        
      elif self.estado == "Maximos":
        if self.wsMcuFactory.debugSerial:        
        	   print "Guardando Matriz Maximos" + '\n' + str(self.matrizMaximos)
    
        f = open("matrizMax.dat","w")
        f.write(str(self.matrizMaximos))
        
        f.close
      

   ##Sobreescritura de la  Matriz actual con los datos del archivo "matrizMax/Min.dat"
   def cargarMatriz(self):      
      ##[MINIMOS]
      if self.estado == "Minimos":
        ##Vamos a escribir sobre la matrizMinimos asi que cambiamos de estado, 
        ##para evitar la colision de datos, y luego volvemos al estado anterior
        estadoAnterior = self.estado      
        self.estado = "Raw"
  
        f = open("matrizMin.dat","r")
        matrizLectura = f.read()
  
        ##Eliminamos los corchetes para poder extraer los valores
        matrizLectura = matrizLectura.replace("[","");
        matrizLectura = matrizLectura.replace("]","");
        count = 0
        
        ## Recorremos la matrizLectura, para extraer los valores en matrizMinimos
        for valor in matrizLectura.split(','):
           row = int(round(count % 16))
           col = int(round(count / 16))
           self.matrizMinimos[col][row] = int(float(valor))         
           count = count +1
           
        f.close
        self.estado = estadoAnterior
        
        if self.wsMcuFactory.debugSerial:
        	print "Cargando matrizMinimos...\n"+ str(self.matrizMinimos)
      ##[MAXIMOS]
      elif self.estado == "Maximos":
        ##Vamos a escribir sobre la matrizMaximos asi que cambiamos de estado, 
        ##para evitar la colision de datos, y luego volvemos al estado anterior
        estadoAnterior = self.estado      
        self.estado = "Raw"
  
        f = open("matrizMax.dat","r")
        matrizLectura = f.read()
  
        ##Eliminamos los corchetes para poder extraer los valores
        matrizLectura = matrizLectura.replace("[","");
        matrizLectura = matrizLectura.replace("]","");
        count = 0
        
        ## Recorremos la matrizLectura, para extraer los valores en matrizMaximos
        for valor in matrizLectura.split(','):
           row = int(round(count % 16))
           col = int(round(count / 16))
           self.matrizMaximos[col][row] = int(float(valor))         
           count = count +1
           
        f.close
        self.estado = estadoAnterior
        
        if self.wsMcuFactory.debugSerial:
        	print "Cargando Matriz Maximos...\n"+ str(self.matrizMaximos)
      

   ##Reiniciamos la  Matriz a 0
   def resetMatriz(self):
      ##[MINIMOS]
      if self.estado == "Minimos":
        if self.wsMcuFactory.debugSerial:
        	print "Reiniciando la matrizMinimos"
        self.matrizMinimos = [[self.maxVal for j  in range (self.dimension1)] for i in range (self.dimension2)]    
      ##[MAXIMOS]    
      elif self.estado == "Maximos":
        if self.wsMcuFactory.debugSerial:
        	print "Reiniciando la Matriz Maximos"
        self.matrizMaximos = [[self.maxVal for j  in range (self.dimension1)] for i in range (self.dimension2)]


## WS-MCU protocol
##
class WsMcuProtocol(WampServerProtocol):

   def onSessionOpen(self):
      ## register topic prefix under which we will publish MCU measurements
      ##
      self.registerForPubSub("http://example.com/mcu#", True)

      ## register methods for RPC
      ##
      self.registerForRpc(self.factory.mcuProtocol, "http://example.com/mcu-control#")
      self.registerForRpc(self.factory.mcuProtocol, "http://example.com/mcu-enviar#")
      self.registerForRpc(self.factory.mcuProtocol, "http://example.com/mcu-consola#")            



## WS-MCU factory
##
class WsMcuFactory(WampServerFactory):

   protocol = WsMcuProtocol

   def __init__(self, url, debugSerial = False, debugWs = False, debugWamp = False):
      WampServerFactory.__init__(self, url, debug = debugWs, debugWamp = debugWamp)
      self.debugSerial = debugSerial
      self.mcuProtocol = McuProtocol(self)


if __name__ == '__main__':

   ## parse options
   ##
   o = Serial2WsOptions()
   try:
      o.parseOptions()
   except usage.UsageError, errortext:
      print '%s %s' % (sys.argv[0], errortext)
      print 'Try %s --help for usage details' % sys.argv[0]
      sys.exit(1)

   debugWs = bool(o.opts['debugws'])
   debugWamp = bool(o.opts['debugwamp'])
   debugSerial = bool(o.opts['debugserial'])
   baudrate = int(o.opts['baudrate'])
   port = o.opts['port']
   webport = int(o.opts['webport'])
   wsurl = o.opts['wsurl']

   ## start Twisted log system
   ##
   log.startLogging(sys.stdout)

   ## create Serial2Ws gateway factory
   ##
   wsMcuFactory = WsMcuFactory(wsurl, debugSerial = debugSerial, debugWs = debugWs, debugWamp = debugWamp)
   listenWS(wsMcuFactory)

   ## create serial port and serial port protocol
   ##
   log.msg('About to open serial port %s [%d baud] ..' % (port, baudrate))
   serialPort = SerialPort(wsMcuFactory.mcuProtocol, port, reactor, baudrate = baudrate)

   ## create embedded web server for static files
   ##
   webdir = File(".")
   web = Site(webdir)
   reactor.listenTCP(webport, web)

   ## start Twisted reactor ..
   ##
   reactor.run()

