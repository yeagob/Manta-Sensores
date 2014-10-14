
    //Conversión del valor del sensor a nuestra escala de colores (de azul a rojo)
   function mapearColor(val) {
		var rgb = new Array(0,0,0);
    var rango = 256;
		//primer 25% del rango de valores      
		if (val <= Math.round(rango/4)) {
		    rgb[0] = 0;
		    rgb[1] = Math.round((val*255)/64);
		    rgb[2] = 255;	  
	  }
	  // Del 25% al 50% del rango de valores
	  if (val > Math.round(rango/4) && val <= Math.round(rango/2)) {
	    rgb[0] = 0;
	    rgb[1] = 255;
	    rgb[2] = 255 - Math.round((val-64)*255/64);
	  }       
	  // Del 50% al 75% del rango de valores
	  if (val > Math.round(rango/2) && val <= Math.round((rango/4)*3)) {
	    rgb[0] = Math.round(((val-128)*255)/64);
	    rgb[1] = 255;
	    rgb[2] = 0;
	  }
	  // Del 75% al 100% del rango de valores
	  if (val > Math.round((rango/4)*3) && val <= rango) {
	    rgb[0] = 255;
	    rgb[1] = 255 - Math.round((val-192)*255/64);
	    rgb[2]= 0;
	  }	

	  return rgb;		
  }
     
     //Control de eventos por segundo
     function speed() {
        var fec = new Date();
        eventCnt++;
        if ( fec.getSeconds() != secondsCnt) {                      
          document.getElementById("analog0").innerHTML= eventCnt.toString();
           secondsCnt = fec.getSeconds();             
          eventCnt = 0
        }          
     }
     
     
     //Formateo de la hora para el log
     function time() {
        var fec = new Date();
        return  fec.getHours()+":"+fec.getMinutes()+":"+fec.getSeconds();
     
     }

   //Contador de refresco de evntos
    function updateEventCnt() {
  		//eventCnt += 1;
    }
    

 	 //Control de estados de lectura, para calibrados y raw. Cargar, guardar y resetear.
     function control(status) {
        //LLamamos a 'rpc:control' en phyton, enviando el cambio de estado
        sess.call("rpc:control", status).always(ab.log);                  
        
        switch(status) {
          case 0: 
            document.formulario.box.value += time()+">Estado: Mínimos\n";
            estado = 0;
          break;

          case 1: 
            document.formulario.box.value += time()+">Estado: Maximos\n";
            estado = 1;
          break;

          case 2: 
            document.formulario.box.value += time()+">Estado: Raw\n";
            estado = 2;
          break;

          case 3: 
            document.formulario.box.value +=  time()+">Estado: Calibrado\n";
            estado = 3;
          break;

          case 4: 
            document.formulario.box.value += time()+">Test de Color\n";
          break;            

          case 5: 
            if (estado == 1)
              document.formulario.box.value += time()+">Guardando Máximos...\n";
            else if (estado == 0)
              document.formulario.box.value += time()+">Guardando Mínimos...\n";
            else
              document.formulario.box.value += time()+">Sin Acción.\n";
          break;

          case 6:
            if (estado == 1) 
              document.formulario.box.value += time()+">Cargando Máximos...\n";
            else if (estado == 0)
              document.formulario.box.value += time()+">Cargando Mínimos...\n";
            else
              document.formulario.box.value += time()+">Sin Acción.\n";
          break;

          case 7: 
            if (estado == 1) 
              document.formulario.box.value += time()+">Reseteando Máximos...\n";
            else if (estado == 0)
              document.formulario.box.value += time()+">Reseteando Mínimos...\n";
            else
              document.formulario.box.value += time()+">Sin Acción.\n";
          break;

          case 8:
             if (buffering) {
                document.formulario.box.value += time()+">Buffer Desactivado\n";
                buffering = false;
             }
             else {
                document.formulario.box.value += time()+">Buffer Activado\n";
                buffering = true;
             }
          break;
                                                                                                                    
        }
     }

       //Conversion de RGB a HEX
       function rgbToHex(r, g, b) {
          return "#" + componentToHex(r) + componentToHex(g) + componentToHex(b);
       }
       
       //Construcción del Hexadecimal
       function componentToHex(c) {
          var hex = c.toString(16);
          return hex.length == 1 ? "0" + hex : hex;
       }
       
      //Establecer la fila/columna que se mostrará en el Smoothie
      function setRowCol () {
            SCol =  document.getElementById("SCol").value;
            SRow =  document.getElementById("SRow").value;
            if (smoothieOn) document.formulario.box.value += time()+">Smoothie monitorizando ["+SCol.toString()+","+SRow.toString()+"]\n" ;
      }
      
      //Monitorización gráfica de sensores individuales. 
	   function CHKsmoothie() {
	        //Si no estaba ya activado, lo creamos
          if (!smoothieOn) {
            //Constructor del Smothie
            var smoothie = new SmoothieChart({grid: {strokeStyle: 'rgb(125, 0, 0)',
                                                     fillStyle: 'rgb(60, 0, 0)',
                                                     lineWidth: 1,
                                                     millisPerLine: 255,
                                                     verticalSections: 6},
                                                     minValue: 0,
                                                     maxValue: 1024,
                                                     resetBounds: false,
                                                     //interpolation: "line"
                                                     });

            //Construimos la grafica con los valores de 'line0'
            smoothie.addTimeSeries(line0, { strokeStyle: 'rgb(0, 255, 0)', fillStyle: 'rgba(0, 255, 0, 0.4)', lineWidth: 3 });

            //Posicionamos la grafica
            smoothie.streamTo(document.getElementById("canvas2"));
            
            //Activamos la variable de control del smoothie y asignamos la fila y columna de monitorización
            smoothieOn = true;
            SCol =  document.getElementById("SCol").value;
            SRow =  document.getElementById("SRow").value;

            //Log
            document.formulario.box.value += time()+">Smoothie monitorizando ["+SCol.toString()+","+SRow.toString()+"]\n" ;
          }
          //Si ya existia lo quitamos
          else
          {
            //Eliminamos el canvas
            var canvasX; 
            canvasX = document.getElementById('canvas2');          
            document.getElementById('divCanvas2').removeChild(canvasX);
            
            //Ponemos el falg a false
            smoothieOn = false;
            
            //Log
            document.formulario.box.value += time()+">Smoothie Off.\n";
             
             //Creamos un nuevo canvas con las mismas caracteristicas. Para posibilitar la reactivación.
            canvasX = document.createElement('canvas');
            canvasX.id = "canvas2";
            canvasX.width = 800;
            canvasX.height = 400;
            document.getElementById('divCanvas2').appendChild(canvasX);
          }
     }
      
    /**
    * Funcion que añade un <li> dentro del <ul>
    */   
    function add_li() 
      {
          var nuevoLi=document.getElementById("nuevo_li").value;
          document.getElementById("nuevo_li").value = "";
          if(nuevoLi.length>0)
          {              
              var li=document.createElement('li');
              li.id=nuevoLi;
              li.innerHTML="<span onclick='eliminar(this)'>X</span>"+nuevoLi;
              document.getElementById("listaDesordenada").appendChild(li);
              
          }
          return false;
      }     
      
    /**
     * Funcion para eliminar los elementos
     * Tiene que recibir el elemento pulsado
     */
    function eliminar(elemento)
    {
        var id=elemento.parentNode.getAttribute("id");
        node=document.getElementById(id);
        node.parentNode.removeChild(node);
    }          
