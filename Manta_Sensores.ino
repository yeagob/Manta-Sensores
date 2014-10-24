/*
* Sketch Arduino, para la lectura de una matriz de sensores de presión, con un 
* demultiplexor para enviar los voltajes(filas) y un multiplexor para leer la 
* señal(columnas). Y envío de la información a través del serial, al 
* microprocesador. 
* Comunicación desde el panel de control, para cambios de estado: Lectura por 
* Resistencia, por condensador y variación de los tiempos de envío de señal (Delaytime)
*/

//Definimos los pines del MUX1 / variables de Señal
#define S0  2
#define S1  3
#define S2  4 
#define S3  5
#define SIG_PIN  A0

//Definimos los pines del MUX2 / variables de Voltaje
#define V0  8
#define V1  9
#define V2  10
#define V3  11
#define VOL_PIN  A1

//Definimos el pin de lectura por condesador
#define FRSpin  7

//Puerto de comunicaciones
HardwareSerial *port;

//Matriz de 16x4 para las conversiones a binario de los numeros de 0 a 15
bool metaMask[16][4] = {
  {0,0,0,0},
  {1,0,0,0},
  {0,1,0,0},
  {1,1,0,0},
  {0,0,1,0},
  {1,0,1,0},
  {0,1,1,0},
  {1,1,1,0},
  {0,0,0,1},
  {1,0,0,1},
  {0,1,0,1},
  {1,1,0,1},
  {0,0,1,1},
  {1,0,1,1},
  {0,1,1,1},
  {1,1,1,1}
};


//Modo de lectura de la manta
bool lecturaResistencia = true;

//Para la recepción de comunicación 
int newValue = 0;

//Control de ciclos/s
long tiempoInicial;
int ciclos;

//Intervalo en microsegundos, entre lecturas de sensoras
int delayTime = 500;


void setup(){
  //Para el debug
   Serial.begin(115200);   
  
 //delay(90000); //Para evitar la 
    
  //Abrimos la comunicación con el microprocesador
  port = &Serial1; // Arduino Yun
  port->begin(57600);
  
  
  //Definimos el estado de los pines de los multiplexores 
  pinMode(S0, OUTPUT); 
  pinMode(S1, OUTPUT); 
  pinMode(S2, OUTPUT); 
  pinMode(S3, OUTPUT); 
  pinMode(SIG_PIN, INPUT);

  pinMode(V0, OUTPUT); 
  pinMode(V1, OUTPUT); 
  pinMode(V2, OUTPUT); 
  pinMode(V3, OUTPUT);   
  pinMode(VOL_PIN, OUTPUT);

  //Inicializamos el control de ciclos
  tiempoInicial = millis();
  ciclos=0;
   
  // Chivato, led pin 13
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);
  //digitalWrite(13, HIGH);
 
}

//Analizamos la información recibida del microprocesador, para modificar el 
//estado del Arduino 
void analisisValue(int b)  {
  
  //Si el valor que llega es numérco
  if (b >= 48 && b <= 57)  {
     if (newValue > 0)
        newValue *= 10;
     newValue +=  (b-48);
  
  }
  else {
    //Si es una instrucción abreviada del significado del valor
    //Delay time
    if (b == 'd') {
        delayTime = newValue;
        Serial.print (delayTime);
        Serial.println (" Nuevo delaytime");    
        newValue = 0;  
     }
     //Cambio de modo a lectura por condensador 
     if (b == 'c') {
       Serial.println (" Lectura por Condensador");  
       lecturaResistencia = false;
     }
     //Cambio de modo a lectura por resistencia     
     if (b == 'r') {
       lecturaResistencia = true;
         Serial.println (" Lectura por Resistencia");
       }
  }
}

//Proceso loop del arduino, lectura de sensores y envío de información
void loop () {
   
   // Control de comandos recibidos por el serial, desde el panel de control.   
   if (port->available()) {
      //Recibimos el valor en inByte
      int inByte = (int)port->read();    
      analisisValue (inByte);   
   }  
  
  
    //Recorremos las filas del mMUX
    for (byte rowCount = 0; rowCount < 16; rowCount++){
    
      // Mandamos voltaje por cada puerta
      digitalWrite(V0, metaMask[rowCount][0]);
      digitalWrite(V1, metaMask[rowCount][1]);
      digitalWrite(V2, metaMask[rowCount][2]);
      digitalWrite(V3, metaMask[rowCount][3]);

      // Recorremos las columnas del MUX
      for (byte colCount = 0; colCount < 16; colCount++) {

          // Leemos los datos por cada puerta
          digitalWrite(S0, metaMask[colCount][0]); //send to Digital OUT 1
          digitalWrite(S1, metaMask[colCount][1]); //send to Digital OUT 2
          digitalWrite(S2, metaMask[colCount][2]); //send to Digital OUT 3
          digitalWrite(S3, metaMask[colCount][3]); //send to Digital OUT 4

          //Lectura por resistencia
          if (lecturaResistencia) {
            //Enviamos el voltaje
            digitalWrite(VOL_PIN, HIGH);
            delayMicroseconds (delayTime);
            //Leemos la respuesta
            port->print(analogRead (SIG_PIN));                  
            port->println();           
            digitalWrite(VOL_PIN, LOW);                
          }
          //Lectura por condensador
          else {
          //Enviamos el voltaje y la función RCTime calcula el tiempo de descarga del condensador
            digitalWrite(VOL_PIN, HIGH);
            port->print(RCtime(FRSpin));                  
            port->println();
            digitalWrite(VOL_PIN, LOW);  
          }
          
          //Control de ciclos por segundo
          /*int tiempoTranscurrido = millis();          
          if ((tiempoTranscurrido - tiempoInicial) >= 1000) {
            tiempoInicial = millis();
            Serial.print (ciclos);
            Serial.print (" matrices/s");            
            Serial.println();
            ciclos=0;
            
          }*/
         
          delayMicroseconds (delayTime);         
              
        }
      }
    //enviamos el caracter de control
  port->print(-1);
  port->println();
  
  ciclos++;     
}

//Calculo del tiempo de descarga del condensador. 
int RCtime(int RCpin) {
  
   int reading = 0;  // start with 0
   
    // set the pin to an output and pull to LOW (ground)
    pinMode(RCpin, OUTPUT);
    digitalWrite(RCpin, LOW);
   
    // Now set the pin to an input and...
    pinMode(RCpin, INPUT);
    while (digitalRead(RCpin) == LOW) { // count how long it takes to rise up to HIGH
      reading++;      // increment to keep track of time 
   
      if (reading == 30000) {
        // if we got this far, the resistance is so high
        // its likely that nothing is connected! 
        break;           // leave the loop
      }
  }
  /*Serial.print (reading); 
  Serial.print (" RcTime");            
  Serial.println();*/
  return reading;
}


