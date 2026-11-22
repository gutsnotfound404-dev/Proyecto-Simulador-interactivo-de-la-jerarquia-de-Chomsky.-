# Documentación de la implementación y conceptos aplicados

**Proyecto:** Simulador de la Jerarquía de Chomsky
**Asignatura:** Autómatas, Gramáticas y Lenguajes
**Lenguaje / librerías:** Python 3 y Tkinter (librería estándar)
**Archivo principal:** `jerarquia_chomsky.py`

---

## 1. Objetivo

Diseñar e implementar una aplicación con interfaz gráfica que permita visualizar, simular y validar el comportamiento de los modelos computacionales asociados a los cuatro niveles de la Jerarquía de Chomsky, mostrando en cada caso el recurso de memoria que distingue al modelo: ninguno (estados), pila, cinta acotada y cinta infinita.

## 2. Marco teórico: la Jerarquía de Chomsky

Noam Chomsky clasificó las gramáticas formales en cuatro tipos según la forma de sus reglas de producción. Cada tipo genera una clase de lenguajes que es reconocida por un modelo de autómata específico, y las clases están contenidas unas en otras:

**Tipo 3 ⊂ Tipo 2 ⊂ Tipo 1 ⊂ Tipo 0**

| Tipo | Gramática (forma de las reglas) | Lenguajes | Autómata | Memoria | Ejemplo |
|------|--------------------------------|-----------|----------|---------|---------|
| 3 | A → aB, A → a (lineal por la derecha) | Regulares | AFD / AFN | Solo el estado (finita) | cadenas binarias con número par de 0s |
| 2 | A → γ (un solo no terminal a la izquierda) | Libres de contexto | Autómata de pila | Pila (LIFO), ilimitada | aⁿbⁿ |
| 1 | αAβ → αγβ, con \|γ\| ≥ 1 | Sensibles al contexto | Autómata linealmente acotado (LBA) | Cinta de longitud \|w\| | aⁿbⁿcⁿ |
| 0 | α → β (sin restricciones) | Recursivamente enumerables | Máquina de Turing | Cinta infinita | el lenguaje de la parada, funciones computables |

Cada inclusión es **estricta**: existen lenguajes de un nivel que no pertenecen al nivel inferior (por ejemplo, aⁿbⁿ es libre de contexto pero no regular, y aⁿbⁿcⁿ es sensible al contexto pero no libre de contexto; ambos hechos se demuestran con el lema de bombeo correspondiente).

## 3. Arquitectura del software

### 3.1 Visión general

La aplicación sigue una separación sencilla entre **lógica de la computación** e **interfaz**:

- La lógica (construcción de autómatas, función de transición, simulación) se implementa con funciones y diccionarios de Python sin dependencia de la interfaz, lo que permitió verificarla de forma exhaustiva por separado (sección 8).
- La interfaz usa **Tkinter** (`tk.Canvas` para los dibujos y `ttk` para los controles).

### 3.2 Clases y funciones principales

| Elemento | Responsabilidad |
|----------|-----------------|
| `App` (hereda de `tk.Tk`) | Ventana principal, estilos y navegación entre el menú y los módulos. |
| `MenuFrame` | Panel principal con las cuatro tarjetas de selección de módulo. |
| `SimBase` | **Clase base** de los módulos: barra de controles, ejemplos de prueba, estado, bitácora y navegación sobre la computación. |
| `DFAFrame` | Nivel 3 (AFD). |
| `PDAFrame` | Nivel 2 (autómata de pila). |
| `TMFrame` | Lógica y dibujo comunes de cinta para los niveles 1 y 0. |
| `LBAFrame`, `TuringFrame` | Nivel 1 (cinta acotada) y Nivel 0 (cinta infinita); heredan de `TMFrame`. |
| `draw_graph` | Dibuja un diagrama de estados (nodos en círculo, flechas, bucles, doble círculo para estados finales). |
| `draw_tape` | Dibuja una cinta con cabezal, índices y celdas resaltadas; sirve para cintas finitas e infinitas. |
| `draw_stack` | Dibuja la pila y la animación de apilado/desapilado. |
| `build_dfa`, `run_pda`, `tm_step` | Lógica de simulación de cada modelo. |

### 3.3 Patrón de diseño: la computación como lista de *instantáneas*

Toda computación se modela como una **secuencia de instantáneas** (*snapshots*), donde cada instantánea es un diccionario con la configuración instantánea del modelo y un mensaje para la bitácora:

| Modelo | Contenido de la instantánea |
|--------|----------------------------|
| AFD | estado, posición en la cadena, última transición |
| AP | estado, posición, contenido de la pila, operación (apilar/desapilar) |
| LBA / MT | estado, posición del cabezal, contenido de la cinta, pasos, última regla |

Todas incluyen el campo `final`: `None` mientras la computación continúa, `True` si acepta y `False` si rechaza.

La clase base `SimBase` navega sobre esa lista con un índice (`pos`):

- **Paso ▶**: avanza un elemento; si aún no existe, lo genera con `advance()`.
- **◀ Atrás**: decrementa el índice (no hay que deshacer nada, cada instantánea es una copia independiente).
- **Ejecutar todo**: avanza hasta que `final` deje de ser `None`.
- **Reproducir**: usa `after()` de Tkinter para avanzar periódicamente.

En el AFD y el AP la lista completa se precalcula; en las máquinas de cinta se genera de forma perezosa, porque una máquina de Turing puede no detenerse. Por eso existe un límite de **5000 pasos** tras el cual se rechaza la cadena con el aviso de posible bucle infinito (la parada es indecidible, ver sección 7.4).

Cada módulo implementa solo cuatro métodos: `build_options`, `make_snaps`, `advance` y `render`.

### 3.4 Ejemplos de prueba en la interfaz

Cada módulo tiene un selector **"Ejemplos de prueba"**. En los modelos predefinidos las cadenas están escritas junto a la definición de cada lenguaje (campo `examples`, con cadenas aceptadas y rechazadas). En el AFD, como el lenguaje depende de parámetros, la lista se **genera automáticamente**: se recorren las cadenas más cortas sobre Σ, se simula el autómata y se eligen cadenas aceptadas y rechazadas repartidas por longitud.

---

## 4. Nivel 3 — Lenguajes regulares: Autómata Finito Determinista

### 4.1 Definición formal

Un AFD es una 5-tupla **M = (Q, Σ, δ, q₀, F)** donde Q es el conjunto finito de estados, Σ el alfabeto, δ: Q × Σ → Q la función de transición (total), q₀ ∈ Q el estado inicial y F ⊆ Q los estados finales. La cadena w se acepta si δ\*(q₀, w) ∈ F.

El AFD no tiene memoria auxiliar: lo único que "recuerda" es su estado actual, que resume una cantidad finita de información sobre lo leído.

### 4.2 Implementación

- La función δ se guarda como un diccionario `{(estado, símbolo): estado_destino}`.
- `make_snaps` lee la cadena símbolo a símbolo, aplica δ y genera una instantánea por símbolo. Si aparece un símbolo fuera de Σ, la cadena se rechaza.
- Las etiquetas de las flechas agrupan todos los símbolos que unen el mismo par de estados (por ejemplo `0,1`).

### 4.3 Lenguajes implementados

1. **Número par de 0s** — dos estados (par/impar). Estado inicial y final: `q0`.
2. **Termina en `ab`** — `q0` = no hay prefijo útil, `q1` = acaba de leerse `a`, `q2` = acaba de leerse `ab` (final).
3. **Binarios divisibles por k (parametrizable)** — los estados `q0 … q(k-1)` representan el **residuo módulo k** del número leído hasta el momento. Al leer un bit d, el número pasa de n a 2n + d, y por tanto el residuo r pasa a
   `δ(qr, d) = q((2r + d) mod k)`. El único estado final es `q0` (residuo 0).
4. **Contiene la subcadena P (parametrizable)** — se construye un autómata con |P| + 1 estados donde `qi` significa "se ha leído el prefijo de P de longitud i que es sufijo de lo leído". Se usa la construcción del autómata de **Knuth–Morris–Pratt (KMP)**: para cada estado se copia la fila de transiciones del *estado de reinicio* X (el estado al que se llegaría tras el prefijo más largo de P que también es sufijo propio), y se sobrescribe la transición del símbolo esperado para avanzar. El estado `q|P|` es final y absorbente.

### 4.4 Por qué son regulares

Cada lenguaje se reconoce con memoria finita, que es exactamente la definición de la clase de lenguajes regulares. Por el contrario, un lenguaje como aⁿbⁿ **no** puede ser reconocido por un AFD (lema de bombeo para regulares): para contar n sería necesario un número ilimitado de estados. Esa necesidad de memoria justifica el siguiente nivel.

---

## 5. Nivel 2 — Lenguajes libres de contexto: Autómata de Pila

### 5.1 Definición formal

Un autómata de pila es una 7-tupla **M = (Q, Σ, Γ, δ, q₀, Z₀, F)**, donde Γ es el alfabeto de la pila y Z₀ ∈ Γ el símbolo de fondo de pila. La transición **δ(q, a, X) = (p, γ)** significa: *en el estado q, leyendo el símbolo a (o ε, sin consumir entrada) con X en el tope, pasar al estado p y reemplazar X por la cadena γ* (con el primer símbolo de γ quedando en el tope).

- γ = ε → **desapilar** X.
- γ = AX → **apilar** A sobre X.
- γ = Y → **reemplazar** el tope.

La aceptación se define por **estado final** con la cadena completamente consumida.

### 5.2 Implementación

- `delta` es un diccionario `{(q, a, X): (p, γ)}`; la cadena vacía se representa con `""`.
- La pila es una lista de Python (el fondo es `stack[0]`, el tope `stack[-1]`).
- `run_pda` es una simulación **determinista**: en cada paso se intenta primero una transición que consuma el siguiente símbolo; si no existe, se intenta una transición ε. Si no hay ninguna, el autómata se detiene. Esto basta para los tres lenguajes elegidos, que admiten un AP determinista.
- Cada paso genera una instantánea con una copia de la pila y el tipo de operación (`push`/`pop`), que `draw_stack` usa para la animación: bloque verde al apilar, bloque rojo punteado con la marca `pop` al desapilar.

### 5.3 Autómatas implementados

**aⁿbⁿ (n ≥ 0)** — se apila una `A` por cada `a`, se desapila una por cada `b`, y se acepta cuando solo queda `Z₀`.

| Transición | Efecto |
|------------|--------|
| δ(q0, a, Z) = (q0, AZ) | primera `a`: apila A |
| δ(q0, a, A) = (q0, AA) | más `a`: apila A |
| δ(q0, b, A) = (q1, ε) | primera `b`: desapila A |
| δ(q1, b, A) = (q1, ε) | más `b`: desapila A |
| δ(q0, ε, Z) = (q2, Z) | cadena vacía: acepta |
| δ(q1, ε, Z) = (q2, Z) | pila vacía de A: acepta |

Estado final: `q2`.

**Paréntesis balanceados** — `(` apila, `)` desapila; si se intenta desapilar con la pila vacía de `A`, no hay transición y se rechaza. Se acepta con ε sobre `Z₀`.

**w c wᴿ** — en `q0` se apila cada símbolo de w (`A` para `a`, `B` para `b`); al leer `c` se pasa a `q1`, donde cada símbolo leído debe coincidir con el tope (así se compara w con wᴿ en orden inverso). Se acepta con ε sobre `Z₀`.

### 5.4 Por qué necesita una pila y por qué no basta

La pila permite **contar y comparar en orden inverso** (aⁿbⁿ, palíndromos con centro, paréntesis anidados). Aun así, aⁿbⁿcⁿ no es libre de contexto (lema de bombeo para libres de contexto): la pila solo puede "recordar" una cantidad al desapilarla, y después ya no queda registro para comparar una tercera. Es el motivo del siguiente nivel.

---

## 6. Nivel 1 — Lenguajes sensibles al contexto: Autómata Linealmente Acotado

### 6.1 Definición

Un **LBA** es una máquina de Turing cuya cinta está limitada a las celdas que ocupa la entrada, encerradas entre dos marcadores de frontera **⊢** y **⊣**. Estos marcadores no se pueden sobrescribir y el cabezal no puede cruzarlos; el espacio de trabajo es, por tanto, lineal en |w|. La clase de lenguajes que reconocen es la de los lenguajes **sensibles al contexto** (tipo 1).

### 6.2 Implementación

- Ambos niveles (1 y 0) comparten el mismo motor `tm_step`, que aplica **una transición** de la forma `δ(q, s) = (q', w, mov)` con mov ∈ {L, R, S}. La diferencia está en el parámetro `bounded`.
- La cinta se guarda como un **diccionario** `{posición: símbolo}`. En el LBA se inicializa con `⊢` en la posición 0, la entrada en 1…n y `⊣` en n+1.
- Si el movimiento deja el cabezal fuera de `0 … n+1`, la cadena se rechaza con el mensaje de que intentó salir de los delimitadores.
- `draw_tape` dibuja solo las celdas existentes (sin celdas más allá de ⊢ y ⊣) y desplaza la ventana si la cinta no cabe.
- Las máquinas implementadas son **deterministas** (un caso particular de LBA).

### 6.3 Máquina para aⁿbⁿcⁿ

Estrategia: en cada ronda se marca una `a` (como `X`), la primera `b` (como `Y`) y la primera `c` (como `Z`); al terminar, se verifica que solo queden `Y` y `Z`.

| Estado | Función | Transiciones |
|--------|---------|--------------|
| q0 | salta el delimitador izquierdo | ⊢ → q1, R |
| q1 | busca la siguiente `a` | a → X, q2, R · Y → q5, R · ⊣ → qa |
| q2 | avanza hasta la primera `b` | a,Y → R · b → Y, q3, R |
| q3 | avanza hasta la primera `c` | b,Z → R · c → Z, q4, L |
| q4 | regresa a la última `X` | a,b,Y,Z → L · X → q1, R |
| q5 | ya no hay `a`: comprueba `Y*Z*⊣` | Y → R · Z → q6, R |
| q6 | | Z → R · ⊣ → qa |

Cualquier caso no listado no tiene transición y la cadena se rechaza (por ejemplo, una `b` sobrante en q5 o una `c` de más en q6).

### 6.4 Máquina para #a = #b = #c (en cualquier orden)

En cada ronda se **vuelve al inicio** (⊢) antes de cada búsqueda: se marca una `a` (`X`), luego una `b` (`Y`) y luego una `c` (`Z`), cada una buscada desde el extremo izquierdo porque pueden aparecer en cualquier posición. Cuando ya no quedan `a`, se recorre la cinta hacia la izquierda verificando que no sobre ninguna `b` ni `c`.

### 6.5 Por qué es sensible al contexto

aⁿbⁿcⁿ no es libre de contexto, pero se genera con una gramática sensible al contexto y se reconoce usando como memoria solo las propias celdas de la entrada (marcándolas). Los LBA también muestran el **movimiento bidireccional** del cabezal, indispensable aquí (ir y volver entre grupos).

---

## 7. Nivel 0 — Recursivamente enumerables: Máquina de Turing

### 7.1 Definición formal

Una máquina de Turing es una 7-tupla **M = (Q, Σ, Γ, δ, q₀, □, F)**, con Σ ⊆ Γ \ {□}, □ el símbolo blanco y δ: Q × Γ → Q × Γ × {L, R, S} (parcial). Dispone de una cinta **infinita** en ambos sentidos. Acepta si alcanza un estado de F; si se queda sin transición, rechaza; y puede no detenerse nunca.

### 7.2 Implementación

- Se reutiliza `tm_step` con `bounded = False`. La cinta es un diccionario cuyas celdas ausentes valen blanco, lo que simula una cinta infinita sin reservar memoria. Al escribir un blanco, la celda se elimina del diccionario.
- `draw_tape` centra la ventana en el cabezal y marca con `⋯` que la cinta continúa.
- Se muestran el estado activo, el símbolo leído, la posición del cabezal y el contador de pasos; el alfabeto de cinta Γ se calcula a partir de las transiciones y se muestra en la interfaz.
- Las máquinas de tipo *función* calculan el resultado leyendo el contenido final de la cinta.

### 7.3 Máquinas implementadas

**Suma unaria 1ᵐ+1ⁿ → 1ᵐ⁺ⁿ.** Recorre el primer bloque, convierte `+` en `1`, recorre el segundo bloque y borra el último `1` (el que sobra).

| Estado | Transiciones |
|--------|--------------|
| q0 | 1 → 1, R · + → 1, q1, R |
| q1 | 1 → 1, R · □ → □, q2, L |
| q2 | 1 → □, qa |

**Incremento binario n → n+1.** Va al extremo derecho y propaga el acarreo hacia la izquierda: los `1` pasan a `0` hasta encontrar un `0` (o un blanco), que se convierte en `1`.

| Estado | Transiciones |
|--------|--------------|
| q0 | 0,1 → R · □ → □, q1, L |
| q1 | 1 → 0, L · 0 → 1, qa · □ → 1, qa |

**Palíndromos sobre {a,b}.** Borra el primer símbolo, se desplaza al último y exige que coincida con el borrado (borrándolo también); repite hasta que la cinta queda vacía. Los estados `q1/q2` tratan el caso en que el símbolo borrado fue `a` y `q3/q5` el caso `b`; `q4` regresa al inicio.

### 7.4 Observaciones teóricas

- Un lenguaje es **recursivamente enumerable** si existe una MT que lo acepta (puede no detenerse con las cadenas que no están en el lenguaje) y **decidible** si existe una MT que siempre se detiene.
- El **problema de la parada** es indecidible: no existe un algoritmo que decida, para toda máquina y toda entrada, si la computación termina. Por eso el simulador impone un límite de pasos en lugar de intentar "detectar" los bucles.
- La **tesis de Church–Turing** sostiene que lo que puede calcularse mediante un procedimiento efectivo puede calcularse con una máquina de Turing; las funciones aritméticas de este módulo (suma, incremento) son ejemplos sencillos.

---

## 8. Pruebas y validación

La lógica de simulación se verificó de manera **exhaustiva**, comparando el resultado de cada simulador contra una definición independiente del lenguaje, para todas las cadenas cortas de cada alfabeto (longitud hasta 8 en el AFD, el AP de aⁿbⁿ y paréntesis, y la MT de palíndromos; hasta 7 en el LBA y hasta 5 en w c wᴿ):

| Módulo | Verificación |
|--------|--------------|
| AFD | par de 0s, termina en `ab`, divisible por 5 y contiene `abab` / `aab` comparados con `count`, `endswith`, aritmética entera e `in`. |
| AP | aⁿbⁿ, paréntesis balanceados (contador) y w c wᴿ (comparación con la inversa). |
| LBA | aⁿbⁿcⁿ (expresión regular y conteo) y #a = #b = #c (conteo). |
| MT | suma unaria (m, n entre 0 y 4), incremento binario (0 a 39) y palíndromos (todas las cadenas hasta longitud 8). |

Además se ejecutó la aplicación y se comprobó que **todos los ejemplos de prueba** del selector (92 en total, incluyendo las listas del AFD parametrizable) producen el resultado indicado en su etiqueta.

## 9. Limitaciones y posibles mejoras

- Las máquinas de los niveles 2, 1 y 0 están predefinidas; se podría añadir un editor/cargador de tablas de transición.
- El autómata de pila es determinista. Un lenguaje como wwᴿ (palíndromos sin centro) requiere **no determinismo**, que podría añadirse explorando todas las ramas de la computación.
- Los LBA implementados son deterministas.
- En los autómatas con muchas transiciones el diagrama puede verse cargado; se podría añadir arrastre de nodos o un modo de visualización por tabla.

## 10. Referencias

- Hopcroft, J. E., Motwani, R., Ullman, J. D. *Introducción a la teoría de autómatas, lenguajes y computación*. Pearson.
- Sipser, M. *Introduction to the Theory of Computation*. Cengage.
- Chomsky, N. (1956). *Three models for the description of language*. IRE Transactions on Information Theory.
- Chomsky, N. (1959). *On certain formal properties of grammars*. Information and Control.
- Documentación de Python: módulo `tkinter` — <https://docs.python.org/3/library/tkinter.html>
