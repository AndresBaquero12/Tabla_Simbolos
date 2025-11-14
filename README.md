# Tabla_Simbolos
## Descripcion
Este Repositorio simula un lenguaje de programación análisis léxico, sintáctico y semántico, con generación de código intermedio de tres direcciones. implementa LL1, ETDS. Se escogio el lenguaje de Python puesto que ya habia un trabajo previo donde de se implementaban ejercicios parecidos.

Requisitos
- Python 3

Ejecucion
```bash
python3 Gramatica.py Prueba.txt
```
Al principio tenia problemas al entender el como funciona la Tabla de simbolos pues creia que funcionaba como un soft, pero al final lo que hace como tal es por ejemplo en.
entrada = EntradaTabla("x", "int", 5, 1)   Guarda -> NombreVarible,Tipo,Valor y la linea donde esta.

Al final al implementar la tabla de símbolos se realizo ámbitos anidados para control de memoria y recursos
- Almacena variables.
- Controla la memoria mediante ámbitos anidados.
- Tiene logica de precedencia para variables locales o globales.
