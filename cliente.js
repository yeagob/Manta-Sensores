/***********************************************************
* Cliente.js
*
* Consexión con el web server Autobhan
* Recepción y visualización de los datos.
* Comunicación desde el panel de control con el servidor, 
* para manejar la microcontroladora. 
************************************************************/

       //Conexión con el WS
       var sess = null;
       var wsuri = "ws://" + window.location.hostname + ":9000";

       //Variables de visualización de información en pantalla
       var analog0 = null;
       var tipoLectura = 0;
       var eventCnt = 0;
       var secondsCnt = 0;
       var estado;
       var buffering = false;
       
       //Refresco
       var eventCntUpdateInterval = 0.01;   
       //Rango de valores recibidos
       var rango = 1024;    
       //Construcción de serie de datos para la visualización por Smothie
       var line0 = new TimeSeries();
       var SRow = -1;
       var SCol = -1;
       var smoothieOn = false;
       

       //Llegada de matriz de datos al cliente
       function onAnalogValue(topicUri, event) {
    
         //Definimos un la visualización de datos: canvas de 16x16 casillas, de RGB variable
    	   var rgb = new Array();
    	   var area = 30;	//Máximo 40. Superficie de cada casilla	            
         canvas = document.getElementById('canvas1');
    	   ctx = canvas.getContext('2d');      

         //Recorremos la matriz de datos recibida y la visualizamos en el canvas
    	   for (var row = 0; row < 16; row ++) {           
    		   for (var col = 0; col < 16; col ++) {
    		     var val;       	
    		     
    	       //Valor de llegada desde phyton mapeado a 255, para el color
    			   val = event[row][col] * 255 / rango ;
    	       rgb = mapearColor(val);
    
    	       //Color y dibujador del cuadrado actual
       			 ctx.fillStyle = rgbToHex(rgb[0], rgb[1], rgb[2]);
    			   ctx.fillRect((row)*area,(col)*area, area, area);
             
             
    			   //Impresión del valor de llegada, en texto
    			   ctx.fillStyle = "black";                         
    			   ctx.fillText(event[row][col].toString(), ((row)*area)+2,((col+1)*area)-3);
             
             //Si está activado el smoothie, mostramos el valor de la posición monitorizada, en otro color
             if (smoothieOn && row == SRow && col == SCol) {
                line0.append(new Date().getTime(), event[row][col]);
                document.getElementById("analog1").innerHTML = event[row][col].toString();
                 //Impresión del valor de lectura en texto
    			       ctx.fillStyle = "white";                         
    			       ctx.fillText(event[row][col].toString(), ((row)*area)+2,((col+1)*area)-3);
             }
    						   				    
    		   }                   
    	   }                 
    						
         //Refrescamos la visualización del 'contador de eventos'
    	  speed();
      }
                    
      //Enviamos instruccion a la linea de comandos
      function actualizar() {
          //Linea de comando enviada
    	    var linea = document.getElementById("input").text;
    	    //Actualizamos la consola
          document.formulario.box.value += linea ;    	
    	    //Llamamos a 'rpc:consola' en phyton, enviando la linea de comando
          sess.call("rpc:consola", linea).always(ab.log);    		  
                
     	 }
    
       //Enviamos los valores de cambio de estado a la microcontroladora
       function enviar(elQue) {
          var valores = new Array(0,0,0);                
          
          //Cambiamos el valor de la resistencia variable
          if (elQue == "res") {
              valores[1] = document.getElementById("resist").value;
              document.formulario.box.value += time()+">Funcion en construcción: "+valores[1]+"\n" ;              
          }       
          //Cambiamos el valor del delay de control de la velocidad de lectura
          else if (elQue == "del") {             
              valores[0] = document.getElementById("delay").value;
              document.formulario.box.value += time()+">New Delay(Microseconds): "+valores[0] +"\n" ;
          }            
          //Cambiamos el estado de la lectura: resistencia/condensador
          else if (elQue == "con")  {
            if (tipoLectura == 1) {
                tipoLectura = 0;
                valores[2] =  1;
                document.formulario.box.value += time()+">Lectura por Resistencia.\n" ;
                rango = 1024;
            }
            else {
                tipoLectura = 1;
                valores[2] =  2;
                document.formulario.box.value += time()+">Lectura por Condensador.\n" ;
                rango = 30000;              
            }
          
          }                             
          
          //Enviamos los valores a la función exportada por RPC desde Python
          sess.call("rpc:enviar", valores).always(ab.log);
          
       }     
     
     // Conexión con el WAMP server
     window.onload = function ()
     {                    
     
        // turn on WAMP debug output
        // ab.debug(true, false, false);

        // use jQuery deferreds
        //ab.Deferred = $.Deferred;

        // connect to WAMP server
        ab.connect(wsuri,

           // WAMP session was established
           function (session) {

              sess = session;
              console.log("Connected to " + wsuri);

              statusline.innerHTML = "Connected to " + wsuri;
              retryCount = 0;

              // Valor que recibimos de Python
              sess.prefix("event", "http://example.com/mcu#");
              sess.subscribe("event:analog-value", onAnalogValue);

              sess.prefix("rpc", "http://example.com/mcu-control#");

              //Velocidad de refresco                 
              window.setInterval(updateEventCnt, eventCntUpdateInterval * 1000);
           },

           // WAMP session is gone
           function (code, reason) {
              sess = null;
              console.log(reason);
           }
        );
      
        //inicializamos la consola        
        document.formulario.box.value = time()+">Connected to ws://192.168.240.1:9000\n" ;    
        estado = 0;	   

     };
      
