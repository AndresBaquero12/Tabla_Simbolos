import sys
import time
from typing import Dict, List, Tuple, Optional, Any

# CLASES BÁSICAS
class Token:
    def __init__(self, tipo: str, lexema: str, linea: int, columna: int, valor=None):
        self.tipo = tipo
        self.lexema = lexema
        self.linea = linea
        self.columna = columna
        self.valor = valor

    def __repr__(self):
        return f"Token({self.tipo}, '{self.lexema}', {self.linea}, {self.columna})"

class ErrorSintactico(Exception):
    def __init__(self, token, esperados=None):
        self.token = token
        self.esperados = esperados or []
    
    def __str__(self):
        texto_token = "$" if self.token.tipo == "EOF" else self.token.lexema
        esperados_str = ", ".join(f'"{e}"' for e in self.esperados)
        return f'<{self.token.linea},{self.token.columna}> Error sintáctico: se encontró: "{texto_token}"; se esperaba: {esperados_str}'

class ErrorSemantico(Exception):
    def __init__(self, mensaje: str, token=None):
        self.mensaje = mensaje
        self.token = token
    
    def __str__(self):
        if self.token:
            return f'<{self.token.linea},{self.token.columna}> Error semántico: {self.mensaje}'
        return f'Error semántico: {self.mensaje}'

class NodoAST:
    """Nodo del Árbol de Sintaxis Abstracta"""
    def __init__(self, tipo: str, valor=None):
        self.tipo = tipo
        self.valor = valor
        self.hijos: List['NodoAST'] = []
        self.atributos = {}
        
    def agregar_hijo(self, hijo: 'NodoAST'):
        self.hijos.append(hijo)
    
    def establecer_atributo(self, nombre: str, valor):
        self.atributos[nombre] = valor
    
    def obtener_atributo(self, nombre: str):
        return self.atributos.get(nombre)

# TABLA DE SÍMBOLOS CON ÁMBITOS
class EntradaTabla:
    def __init__(self, nombre: str, tipo: str, valor=None, linea: int = 0):
        self.nombre = nombre
        self.tipo = tipo
        self.valor = valor
        self.linea = linea

class Ambito:
    def __init__(self, padre=None, nombre="global"):
        self.padre = padre
        self.nombre = nombre
        self.simbolos: Dict[str, EntradaTabla] = {}
    
    def agregar(self, nombre: str, tipo: str, valor=None, linea: int = 0) -> bool:
        if nombre in self.simbolos:
            return False
        self.simbolos[nombre] = EntradaTabla(nombre, tipo, valor, linea)
        return True
    
    def buscar_local(self, nombre: str) -> Optional[EntradaTabla]:
        return self.simbolos.get(nombre)
    
    def buscar(self, nombre: str) -> Optional[EntradaTabla]:
        """Búsqueda en todos los ámbitos (recursivamente hacia arriba)"""
        actual = self
        while actual:
            simbolo = actual.buscar_local(nombre)
            if simbolo:
                return simbolo
            actual = actual.padre
        return None
    
    def __str__(self):
        return f"Ámbito({self.nombre}): {list(self.simbolos.keys())}"

# ANALIZADOR LÉXICO EXTENDIDO
SIMBOLOS = {
    "(": "PAR_IZQ",
    ")": "PAR_DER",
    "{": "LLAVE_IZQ", 
    "}": "LLAVE_DER",
    "+": "MAS",
    "-": "MENOS",
    "*": "POR",
    "/": "DIV",
    "=": "ASIG",
    ";": "PUNTO_COMA",
    ",": "COMA",
    "==": "IGUAL",
    "!=": "DIFERENTE",
    "<": "MENOR",
    ">": "MAYOR",
    "<=": "MENOR_IGUAL",
    ">=": "MAYOR_IGUAL",
}

PALABRAS_RESERVADAS = {
    "int": "INT",
    "float": "FLOAT", 
    "if": "IF",
    "while": "WHILE",
    "else": "ELSE",
    "print": "PRINT",
}

class AnalizadorLexico:
    def __init__(self, codigo: str):
        self.codigo = codigo
        self.pos = 0
        self.linea = 1
        self.columna = 1
        self.tokens: List[Token] = []
        self._tokenizar()
    
    def _avanzar_caracter(self):
        if self.pos < len(self.codigo):
            char = self.codigo[self.pos]
            self.pos += 1
            if char == '\n':
                self.linea += 1
                self.columna = 1
            else:
                self.columna += 1
            return char
        return None
    
    def _mirar_siguiente(self):
        if self.pos < len(self.codigo):
            return self.codigo[self.pos]
        return None
    
    def _mirar_siguientes(self, n=1):
        if self.pos + n <= len(self.codigo):
            return self.codigo[self.pos:self.pos+n]
        return None
    
    def _tokenizar(self):
        while self.pos < len(self.codigo):
            char = self._mirar_siguiente()
            
            # Espacios en blanco
            if char in " \t\n\r":
                self._avanzar_caracter()
                continue
            
            # Comentarios de una línea
            if char == '/' and self._mirar_siguientes(2) == "//":
                while char and char != '\n':
                    char = self._avanzar_caracter()
                continue
            
            # Símbolos de 2 caracteres
            if char in "!=<>":
                dos_caracteres = self._mirar_siguientes(2)
                if dos_caracteres in ["==", "!=", "<=", ">="]:
                    inicio_col = self.columna
                    self._avanzar_caracter()
                    self._avanzar_caracter()
                    self.tokens.append(Token(SIMBOLOS[dos_caracteres], dos_caracteres, self.linea, inicio_col))
                    continue
            
            # Símbolos de 1 carácter
            if char in SIMBOLOS:
                inicio_col = self.columna
                self._avanzar_caracter()
                self.tokens.append(Token(SIMBOLOS[char], char, self.linea, inicio_col))
                continue
            
            # Números
            if char.isdigit():
                inicio_col = self.columna
                numero = ""
                tiene_punto = False
                while char and (char.isdigit() or (char == '.' and not tiene_punto)):
                    if char == '.':
                        tiene_punto = True
                    numero += self._avanzar_caracter()
                    char = self._mirar_siguiente()
                valor = float(numero) if tiene_punto else int(numero)
                self.tokens.append(Token("NUMERO", numero, self.linea, inicio_col, valor))
                continue
            
            # Identificadores y palabras reservadas
            if char.isalpha() or char == '_':
                inicio_col = self.columna
                identificador = ""
                while char and (char.isalnum() or char == '_'):
                    identificador += self._avanzar_caracter()
                    char = self._mirar_siguiente()
                
                # Verificar si es palabra reservada
                if identificador in PALABRAS_RESERVADAS:
                    self.tokens.append(Token(PALABRAS_RESERVADAS[identificador], identificador, self.linea, inicio_col))
                else:
                    self.tokens.append(Token("IDENTIFICADOR", identificador, self.linea, inicio_col))
                continue
            
            # Carácter desconocido
            inicio_col = self.columna
            self._avanzar_caracter()
            self.tokens.append(Token("DESCONOCIDO", char, self.linea, inicio_col))
        
        self.tokens.append(Token("EOF", "$", self.linea, self.columna))

# ANALIZADOR SINTÁCTICO CON ETDS
class ParserLL1:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.actual: Token = None
        self.ambito_actual = Ambito()  # Ámbito global inicial
        self._avanzar()
    
    def _avanzar(self):
        if self.pos < len(self.tokens):
            self.actual = self.tokens[self.pos]
            self.pos += 1
    
    def _comer(self, tipo: str) -> Token:
        if self.actual.tipo == tipo:
            token_actual = self.actual
            self._avanzar()
            return token_actual
        else:
            raise ErrorSintactico(self.actual, [tipo])
    
    def _abrir_ambito(self, nombre="local"):
        """Abre un nuevo ámbito (para bloques {})"""
        nuevo_ambito = Ambito(self.ambito_actual, nombre)
        self.ambito_actual = nuevo_ambito
        return nuevo_ambito
    
    def _cerrar_ambito(self):
        """Cierra el ámbito actual y vuelve al padre"""
        if self.ambito_actual.padre:
            self.ambito_actual = self.ambito_actual.padre
    
    def analizar(self) -> NodoAST:
        """Program → {Decl} {Stmt}"""
        nodo_programa = NodoAST("PROGRAMA")
        
        # Declaraciones
        while self.actual.tipo in ["INT", "FLOAT"]:
            decl = self._declaracion()
            nodo_programa.agregar_hijo(decl)
        
        # Statements
        while self.actual.tipo != "EOF":
            stmt = self._statement()
            nodo_programa.agregar_hijo(stmt)
        
        self._comer("EOF")
        return nodo_programa
    
    def _declaracion(self) -> NodoAST:
        """Decl → Type id ;"""
        tipo_token = self.actual
        tipo = self._tipo()
        id_token = self._comer("IDENTIFICADOR")
        self._comer("PUNTO_COMA")
        
        # ETDS: Agregar a tabla de símbolos
        if not self.ambito_actual.agregar(id_token.lexema, tipo, linea=id_token.linea):
            raise ErrorSemantico(f"Variable '{id_token.lexema}' ya declarada", id_token)
        
        nodo = NodoAST("DECLARACION")
        nodo.agregar_hijo(NodoAST("TIPO", tipo))
        nodo.agregar_hijo(NodoAST("ID", id_token.lexema))
        nodo.establecer_atributo("tipo", tipo)
        nodo.establecer_atributo("id", id_token.lexema)
        return nodo
    
    def _tipo(self) -> str:
        """Type → int | float"""
        if self.actual.tipo == "INT":
            self._comer("INT")
            return "int"
        elif self.actual.tipo == "FLOAT":
            self._comer("FLOAT")
            return "float"
        else:
            raise ErrorSintactico(self.actual, ["INT", "FLOAT"])
    
    def _statement(self) -> NodoAST:
        """Stmt → id = Expr ; | if ( Expr ) Stmt | while ( Expr ) Stmt | { {Stmt} } | print Expr ;"""
        if self.actual.tipo == "IDENTIFICADOR":
            return self._asignacion()
        elif self.actual.tipo == "IF":
            return self._if_statement()
        elif self.actual.tipo == "WHILE":
            return self._while_statement()
        elif self.actual.tipo == "LLAVE_IZQ":
            return self._bloque()
        elif self.actual.tipo == "PRINT":
            return self._print_statement()
        else:
            raise ErrorSintactico(self.actual, ["IDENTIFICADOR", "IF", "WHILE", "LLAVE_IZQ", "PRINT"])
    
    def _asignacion(self) -> NodoAST:
        """Stmt → id = Expr ;"""
        id_token = self._comer("IDENTIFICADOR")
        
        # ETDS: Verificar que la variable existe
        simbolo = self.ambito_actual.buscar(id_token.lexema)
        if not simbolo:
            raise ErrorSemantico(f"Variable '{id_token.lexema}' no declarada", id_token)
        
        self._comer("ASIG")
        expr = self._expresion()
        self._comer("PUNTO_COMA")
        
        nodo = NodoAST("ASIGNACION")
        nodo.agregar_hijo(NodoAST("ID", id_token.lexema))
        nodo.agregar_hijo(expr)
        nodo.establecer_atributo("id", id_token.lexema)
        nodo.establecer_atributo("tipo_var", simbolo.tipo)
        return nodo
    
    def _if_statement(self) -> NodoAST:
        """Stmt → if ( Expr ) Stmt [else Stmt]"""
        self._comer("IF")
        self._comer("PAR_IZQ")
        condicion = self._expresion()
        self._comer("PAR_DER")
        
        then_stmt = self._statement()
        
        nodo = NodoAST("IF")
        nodo.agregar_hijo(condicion)
        nodo.agregar_hijo(then_stmt)
        
        if self.actual.tipo == "ELSE":
            self._comer("ELSE")
            else_stmt = self._statement()
            nodo.agregar_hijo(else_stmt)
        
        return nodo
    
    def _while_statement(self) -> NodoAST:
        """Stmt → while ( Expr ) Stmt"""
        self._comer("WHILE")
        self._comer("PAR_IZQ")
        condicion = self._expresion()
        self._comer("PAR_DER")
        
        cuerpo = self._statement()
        
        nodo = NodoAST("WHILE")
        nodo.agregar_hijo(condicion)
        nodo.agregar_hijo(cuerpo)
        return nodo
    
    def _bloque(self) -> NodoAST:
        """Stmt → { {Stmt} }"""
        self._comer("LLAVE_IZQ")
        
        # ETDS: Abrir nuevo ámbito
        self._abrir_ambito("bloque")
        
        nodo = NodoAST("BLOQUE")
        while self.actual.tipo != "LLAVE_DER" and self.actual.tipo != "EOF":
            stmt = self._statement()
            nodo.agregar_hijo(stmt)
        
        self._comer("LLAVE_DER")
        
        # ETDS: Cerrar ámbito
        self._cerrar_ambito()
        
        return nodo
    
    def _print_statement(self) -> NodoAST:
        """Stmt → print Expr ;"""
        self._comer("PRINT")
        expr = self._expresion()
        self._comer("PUNTO_COMA")
        
        nodo = NodoAST("PRINT")
        nodo.agregar_hijo(expr)
        return nodo
    
    def _expresion(self) -> NodoAST:
        """Expr → Expr opsuma Term | Term"""
        nodo_term = self._termino()
        return self._expresion_prima(nodo_term)
    
    def _expresion_prima(self, heredado: NodoAST) -> NodoAST:
        if self.actual.tipo in ["MAS", "MENOS", "IGUAL", "DIFERENTE", "MENOR", "MAYOR", "MENOR_IGUAL", "MAYOR_IGUAL"]:
            operador = self.actual.lexema
            self._avanzar()
            nodo_term = self._termino()
            
            nodo_op = NodoAST("OPERACION", operador)
            nodo_op.agregar_hijo(heredado)
            nodo_op.agregar_hijo(nodo_term)
            
            # ETDS: Calcular tipo de la operación
            tipo_izq = heredado.obtener_atributo("tipo") or "int"
            tipo_der = nodo_term.obtener_atributo("tipo") or "int"
            
            if operador in ["==", "!=", "<", ">", "<=", ">="]:
                nodo_op.establecer_atributo("tipo", "bool")
            elif tipo_izq == "float" or tipo_der == "float":
                nodo_op.establecer_atributo("tipo", "float")
            else:
                nodo_op.establecer_atributo("tipo", "int")
            
            return self._expresion_prima(nodo_op)
        else:
            return heredado
    
    def _termino(self) -> NodoAST:
        """Term → Term opmult Factor | Factor"""
        nodo_factor = self._factor()
        return self._termino_prima(nodo_factor)
    
    def _termino_prima(self, heredado: NodoAST) -> NodoAST:
        if self.actual.tipo in ["POR", "DIV"]:
            operador = self.actual.lexema
            self._avanzar()
            nodo_factor = self._factor()
            
            nodo_op = NodoAST("OPERACION", operador)
            nodo_op.agregar_hijo(heredado)
            nodo_op.agregar_hijo(nodo_factor)
            
            # ETDS: Calcular tipo
            tipo_izq = heredado.obtener_atributo("tipo") or "int"
            tipo_der = nodo_factor.obtener_atributo("tipo") or "int"
            
            if tipo_izq == "float" or tipo_der == "float":
                nodo_op.establecer_atributo("tipo", "float")
            else:
                nodo_op.establecer_atributo("tipo", "int")
            
            return self._termino_prima(nodo_op)
        else:
            return heredado
    
    def _factor(self) -> NodoAST:
        """Factor → ( Expr ) | id | num"""
        if self.actual.tipo == "PAR_IZQ":
            self._comer("PAR_IZQ")
            nodo_expr = self._expresion()
            self._comer("PAR_DER")
            return nodo_expr
        elif self.actual.tipo == "NUMERO":
            token = self._comer("NUMERO")
            nodo = NodoAST("NUMERO", token.valor)
            # ETDS: Determinar tipo del número
            tipo = "float" if isinstance(token.valor, float) else "int"
            nodo.establecer_atributo("tipo", tipo)
            return nodo
        elif self.actual.tipo == "IDENTIFICADOR":
            token = self._comer("IDENTIFICADOR")
            
            # ETDS: Verificar que la variable existe
            simbolo = self.ambito_actual.buscar(token.lexema)
            if not simbolo:
                raise ErrorSemantico(f"Variable '{token.lexema}' no declarada", token)
            
            nodo = NodoAST("IDENTIFICADOR", token.lexema)
            nodo.establecer_atributo("tipo", simbolo.tipo)
            return nodo
        else:
            raise ErrorSintactico(self.actual, ["PAR_IZQ", "NUMERO", "IDENTIFICADOR"])

# GENERADOR DE CÓDIGO DE TRES DIRECCIONES (CORREGIDO)
class GeneradorTresDirecciones:
    def __init__(self):
        self.codigo: List[str] = []
        self.temporales: List[Tuple[str, str]] = []
        self.contador_temp = 0
        self.contador_etiqueta = 0
        self.variables_declaradas = set()
    
    def _nuevo_temporal(self, tipo="float") -> str:
        temp = f"t{self.contador_temp}"
        self.contador_temp += 1
        self.temporales.append((temp, tipo))
        return temp
    
    def _nueva_etiqueta(self) -> str:
        etiqueta = f"L{self.contador_etiqueta}"
        self.contador_etiqueta += 1
        return etiqueta
    
    def generar(self, nodo: NodoAST) -> str:
        """Genera código de tres direcciones para el AST"""
        if nodo.tipo == "PROGRAMA":
            for hijo in nodo.hijos:
                self.generar(hijo)
            return ""
        
        elif nodo.tipo == "DECLARACION":
            # Generar declaración en código de 3 direcciones
            id_nombre = nodo.obtener_atributo("id")
            tipo = nodo.obtener_atributo("tipo")
            if id_nombre not in self.variables_declaradas:
                self.codigo.append(f"DECLARE {id_nombre} {tipo}")
                self.variables_declaradas.add(id_nombre)
            return ""
        
        elif nodo.tipo == "ASIGNACION":
            id_nombre = nodo.obtener_atributo("id")
            expr_temp = self.generar(nodo.hijos[1])
            # Asignación simple
            self.codigo.append(f"{id_nombre} = {expr_temp}")
            return id_nombre
        
        elif nodo.tipo == "OPERACION":
            izquierda = self.generar(nodo.hijos[0])
            derecha = self.generar(nodo.hijos[1])
            operador = nodo.valor
            
            # Mapear operadores a instrucciones de tres direcciones
            mapeo_ops = {
                '+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV',
                '==': 'EQ', '!=': 'NE', '<': 'LT', '>': 'GT',
                '<=': 'LE', '>=': 'GE'
            }
            
            temp = self._nuevo_temporal(nodo.obtener_atributo("tipo") or "float")
            
            if operador in mapeo_ops:
                # FORMATO CORRECTO: temp = OP arg1 arg2
                instruccion = f"{temp} = {mapeo_ops[operador]} {izquierda} {derecha}"
            else:
                # Para operadores no mapeados (fallback)
                instruccion = f"{temp} = {izquierda} {operador} {derecha}"
            
            self.codigo.append(instruccion)
            return temp
        
        elif nodo.tipo == "NUMERO":
            return str(nodo.valor)
        
        elif nodo.tipo == "IDENTIFICADOR":
            return nodo.valor
        
        elif nodo.tipo == "IF":
            cond_temp = self.generar(nodo.hijos[0])
            etiqueta_else = self._nueva_etiqueta()
            etiqueta_fin = self._nueva_etiqueta()
            
            # IF-GOTO con condición negada
            self.codigo.append(f"IFFALSE {cond_temp} GOTO {etiqueta_else}")
            
            # Bloque THEN
            self.generar(nodo.hijos[1])
            self.codigo.append(f"GOTO {etiqueta_fin}")
            
            # Bloque ELSE
            self.codigo.append(f"{etiqueta_else}:")
            if len(nodo.hijos) > 2:
                self.generar(nodo.hijos[2])
            
            self.codigo.append(f"{etiqueta_fin}:")
            return ""
        
        elif nodo.tipo == "WHILE":
            inicio = self._nueva_etiqueta()
            fin = self._nueva_etiqueta()
            
            self.codigo.append(f"{inicio}:")
            cond_temp = self.generar(nodo.hijos[0])
            self.codigo.append(f"IFFALSE {cond_temp} GOTO {fin}")
            
            self.generar(nodo.hijos[1])
            self.codigo.append(f"GOTO {inicio}")
            self.codigo.append(f"{fin}:")
            return ""
        
        elif nodo.tipo == "BLOQUE":
            for hijo in nodo.hijos:
                self.generar(hijo)
            return ""
        
        elif nodo.tipo == "PRINT":
            expr_temp = self.generar(nodo.hijos[0])
            self.codigo.append(f"PRINT {expr_temp}")
            return ""
        
        return ""
    
    def obtener_codigo(self) -> List[str]:
        return self.codigo
    
    def limpiar(self):
        self.codigo.clear()
        self.temporales.clear()
        self.contador_temp = 0
        self.contador_etiqueta = 0
        self.variables_declaradas.clear()

# DECORADOR DE AST (Análisis Semántico)
class DecoradorAST:
    def __init__(self, parser: ParserLL1):
        self.parser = parser
    
    def decorar(self, nodo: NodoAST) -> Any:
        """Realiza el análisis semántico y decora el AST con atributos"""
        if nodo.tipo == "PROGRAMA":
            for hijo in nodo.hijos:
                self.decorar(hijo)
            return None
        
        elif nodo.tipo == "DECLARACION":
            return None
        
        elif nodo.tipo == "ASIGNACION":
            tipo_var = nodo.obtener_atributo("tipo_var")
            tipo_expr = self.decorar(nodo.hijos[1])
            
            # Verificar compatibilidad de tipos
            if tipo_var != tipo_expr and not (tipo_var == "float" and tipo_expr == "int"):
                raise ErrorSemantico(f"No se puede asignar {tipo_expr} a variable de tipo {tipo_var}")
            
            return None
        
        elif nodo.tipo == "OPERACION":
            tipo_izq = self.decorar(nodo.hijos[0])
            tipo_der = self.decorar(nodo.hijos[1])
            
            # Operaciones relacionales siempre devuelven bool
            if nodo.valor in ["==", "!=", "<", ">", "<=", ">="]:
                return "bool"
            
            # Operaciones aritméticas
            if tipo_izq == "float" or tipo_der == "float":
                return "float"
            else:
                return "int"
        
        elif nodo.tipo == "NUMERO":
            return "float" if isinstance(nodo.valor, float) else "int"
        
        elif nodo.tipo == "IDENTIFICADOR":
            simbolo = self.parser.ambito_actual.buscar(nodo.valor)
            return simbolo.tipo if simbolo else "int"
        
        elif nodo.tipo in ["IF", "WHILE", "BLOQUE", "PRINT"]:
            for hijo in nodo.hijos:
                self.decorar(hijo)
            return None
        
        return None

# VISUALIZADOR
class VisualizadorSimple:
    @staticmethod
    def imprimir_arbol_simple(nodo: NodoAST, prefijo: str = "", es_ultimo: bool = True) -> List[str]:
        lineas = []
        conector = "└─ " if es_ultimo else "├─ "
        
        # Información del nodo
        if nodo.tipo == "OPERACION":
            simbolo = {"+": "Suma (+)", "-": "Resta (-)", "*": "Multiplicación (*)", "/": "División (/)"}
            info = simbolo.get(nodo.valor, f"Operación ({nodo.valor})")
            tipo = nodo.obtener_atributo("tipo")
            if tipo:
                info += f" [{tipo}]"
        elif nodo.tipo == "UNARIO":
            info = f"Operador unario ({nodo.valor})"
        elif nodo.tipo == "NUMERO":
            info = f"Número: {nodo.valor}"
            tipo = nodo.obtener_atributo("tipo")
            if tipo:
                info += f" [{tipo}]"
        elif nodo.tipo == "IDENTIFICADOR":
            info = f"Variable: {nodo.valor}"
            tipo = nodo.obtener_atributo("tipo")
            if tipo:
                info += f" [{tipo}]"
        elif nodo.tipo == "DECLARACION":
            tipo = nodo.obtener_atributo("tipo")
            id_nombre = nodo.obtener_atributo("id")
            info = f"Declaración: {id_nombre} [{tipo}]"
        elif nodo.tipo == "ASIGNACION":
            id_nombre = nodo.obtener_atributo("id")
            info = f"Asignación: {id_nombre}"
        else:
            info = nodo.tipo
        
        lineas.append(prefijo + conector + info)
        
        # Hijos
        if nodo.hijos:
            extension = "   " if es_ultimo else "│  "
            nuevo_prefijo = prefijo + extension
            for i, hijo in enumerate(nodo.hijos):
                es_ultimo_hijo = (i == len(nodo.hijos) - 1)
                lineas.extend(VisualizadorSimple.imprimir_arbol_simple(hijo, nuevo_prefijo, es_ultimo_hijo))
        
        return lineas

# FUNCIÓN PRINCIPAL DE ANÁLISIS
def analizar_programa(codigo: str) -> str:
    """Analiza un programa completo y genera código de tres direcciones"""
    
    resultado = []
    tiempo_inicio = time.time()

    resultado.append("╔═══════════════════════════════════════════════════════════════════════════╗")
    resultado.append("║  ANALIZADOR DE PROGRAMAS CON GENERACIÓN DE CÓDIGO DE 3 DIRECCIONES      ║")
    resultado.append("╚═══════════════════════════════════════════════════════════════════════════╝")
    resultado.append("")
    resultado.append(f"Programa:")
    resultado.append(f"```")
    resultado.append(codigo)
    resultado.append(f"```")
    resultado.append("")
    
    try:
        # Análisis léxico
        lexer = AnalizadorLexico(codigo)
        errores_lexicos = [t for t in lexer.tokens if t.tipo == "DESCONOCIDO"]
        
        if errores_lexicos:
            resultado.append("╔════════════════════════════════════════════════════════════════════╗")
            resultado.append("║  [ERROR LÉXICO]                                                    ║")
            resultado.append("╚════════════════════════════════════════════════════════════════════╝")
            resultado.append("")
            for error in errores_lexicos:
                resultado.append(f"   ❌ Carácter inválido '{error.lexema}' en línea {error.linea}, columna {error.columna}")
            return '\n'.join(resultado)
        
        # Análisis sintáctico y semántico
        parser = ParserLL1(lexer.tokens)
        ast = parser.analizar()
        
        # Análisis semántico
        decorador = DecoradorAST(parser)
        decorador.decorar(ast)
        
        # Generación de código de tres direcciones
        generador = GeneradorTresDirecciones()
        generador.generar(ast)
        
        # SALIDA EXITOSA
        resultado.append("╔════════════════════════════════════════════════════════════════════╗")
        resultado.append("║  ✅ ANÁLISIS EXITOSO                                               ║")
        resultado.append("╚════════════════════════════════════════════════════════════════════╝")
        resultado.append("")
        
        # Tabla de símbolos
        resultado.append("┌────────────────────────────────────────────────────────────────────┐")
        resultado.append("│  TABLA DE SÍMBOLOS (Ámbito global)                                 │")
        resultado.append("└────────────────────────────────────────────────────────────────────┘")
        if parser.ambito_actual.simbolos:
            for nombre, entrada in parser.ambito_actual.simbolos.items():
                resultado.append(f"   • {nombre:<15} : {entrada.tipo:<8} (línea {entrada.linea})")
        else:
            resultado.append("   (sin variables declaradas)")
        resultado.append("")
        
        # Código de tres direcciones generado
        resultado.append("┌────────────────────────────────────────────────────────────────────┐")
        resultado.append("│  CÓDIGO DE TRES DIRECCIONES GENERADO                               │")
        resultado.append("└────────────────────────────────────────────────────────────────────┘")
        if generador.obtener_codigo():
            for i, instruccion in enumerate(generador.obtener_codigo(), 1):
                resultado.append(f"   {i:3d}. {instruccion}")
        else:
            resultado.append("   (sin código generado)")
        resultado.append("")
        
        # Temporales utilizados
        if generador.temporales:
            resultado.append("┌────────────────────────────────────────────────────────────────────┐")
            resultado.append("│  VARIABLES TEMPORALES                                              │")
            resultado.append("└────────────────────────────────────────────────────────────────────┘")
            for temp, tipo in generador.temporales:
                resultado.append(f"   • {temp:<10} : {tipo}")
            resultado.append("")
        
        # Árbol AST
        resultado.append("┌────────────────────────────────────────────────────────────────────┐")
        resultado.append("│  ÁRBOL DE SINTAXIS ABSTRACTA (AST)                                 │")
        resultado.append("└────────────────────────────────────────────────────────────────────┘")
        lineas_arbol = VisualizadorSimple.imprimir_arbol_simple(ast)
        for linea in lineas_arbol:
            resultado.append("   " + linea)
        resultado.append("")
        
    except ErrorSintactico as e:
        resultado.append("╔════════════════════════════════════════════════════════════════════╗")
        resultado.append("║  ❌ [ERROR SINTÁCTICO]                                             ║")
        resultado.append("╚════════════════════════════════════════════════════════════════════╝")
        resultado.append("")
        resultado.append(f"   {e}")
        return '\n'.join(resultado)
    
    except ErrorSemantico as e:
        resultado.append("╔════════════════════════════════════════════════════════════════════╗")
        resultado.append("║  ❌ [ERROR SEMÁNTICO]                                              ║")
        resultado.append("╚════════════════════════════════════════════════════════════════════╝")
        resultado.append("")
        resultado.append(f"   {e}")
        return '\n'.join(resultado)
    
    except Exception as e:
        resultado.append("╔════════════════════════════════════════════════════════════════════╗")
        resultado.append("║  ⚠️  [ERROR INESPERADO]                                            ║")
        resultado.append("╚════════════════════════════════════════════════════════════════════╝")
        resultado.append("")
        resultado.append(f"   {e}")
        import traceback
        resultado.append(f"   {traceback.format_exc()}")
        return '\n'.join(resultado)
    
    # Tiempo de ejecución
    tiempo_fin = time.time()
    tiempo_total = tiempo_fin - tiempo_inicio
    resultado.append("─" * 72)
    resultado.append(f"⏱️  Tiempo de ejecución: {tiempo_total:.4f} segundos")
    resultado.append("")
    
    return '\n'.join(resultado)

def main():
    if len(sys.argv) != 2:
        print("╔═══════════════════════════════════════════════════════════════════════════╗")
        print("║  ANALIZADOR DE PROGRAMAS CON GENERACIÓN DE CÓDIGO DE 3 DIRECCIONES      ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        print("")
        print("Uso:")
        print("  python compilador.py <archivo.txt>")
        print("")
        print("Ejemplo:")
        print("  python compilador.py programa.txt")
        print("")
        sys.exit(1)

    archivo = sys.argv[1]

    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()

        if not contenido:
            print(f"[Error] El archivo '{archivo}' está vacío")
            sys.exit(1)

        print(f"\n📂 [Analizando programa desde: {archivo}]\n")

        resultado = analizar_programa(contenido)
        print(resultado)

        # Guardar resultado
        nombre_salida = archivo.replace('.txt', '_output.txt')
        with open(nombre_salida, "w", encoding="utf-8") as f:
            f.write(resultado)

        print(f"\n💾 [Resultados guardados en: {nombre_salida}]")

    except FileNotFoundError:
        print(f"❌ [Error] No se encontró el archivo '{archivo}'")
        sys.exit(1)
    except Exception as e:
        print(f"⚠️  [Error inesperado] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()