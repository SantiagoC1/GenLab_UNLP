# Escenarios: Laboratorio de genética (exoma clínico), versión 3

**Metodología:** escenarios según Julio Cesar Sampaio do Prado Leite (escenarios futuros: describen cómo opera el dominio con el sistema).
**Fuente de reglas de negocio:** transcripción depurada de la entrevista al Product Owner (v2).
**Vocabulario:** `LEL_Laboratorio_Corregido.md`. Los identificadores P1 a P17 y D1 se explican en la sección "Pendientes y decisiones" del final.
**Uso:** base para el prototipo de interfaces en Figma.
**Cambios:** esta versión unifica la revisión de los escenarios 1 a 22 con la corrección de los escenarios restantes hecha por el grupo. El detalle está en la sección "Cambios respecto de la v2".

## Convenciones

- Los términos en **negrita** son símbolos del LEL corregido, usados sin sinónimos.
- Un nombre en MAYÚSCULAS dentro de un episodio invoca a otro escenario (subescenario), según la convención de Leite. El comportamiento se describe una sola vez y se referencia desde donde se necesita.
- El título de cada escenario empieza con un verbo en infinitivo, y siempre que fue posible coincide con un verbo del LEL.
- Cada episodio tiene un sujeto y una acción del dominio. Se evitaron los verbos genéricos de formulario (seleccionar, ingresar, validar, confirmar).
- Las restricciones y reglas de negocio se escriben en el **Contexto**, como "Restricción", y no como excepciones.
- Las **Excepciones** son solo obstáculos reales que impiden alcanzar el objetivo. Si la entrevista no menciona ninguno, se indica "Ninguna identificada".
- Lo que la entrevista no cierra se indica en el **Contexto** como "Pendiente (Pn)".
- **[deseo]** marca una funcionalidad pedida por el PO pero condicionada al costo o a la factibilidad. **[supuesto]** marca un detalle que no surge de la entrevista y que el equipo decidió para poder continuar.

---

## Catálogo de estados

Base común para todos los escenarios. Cada estado pertenece a una dimensión distinta, y no toda operación genera un estado nuevo.

### Ciclo de vida del estudio

Es una dimensión excluyente: el **estudio** está en un solo estado a la vez.

| Estado | Lo produce el escenario | Origen |
|---|---|---|
| **Creado** | 10 | Lo nombra el PO |
| **Autorizado** / **Rechazado** | 18 | El PO lo describe como resultado de la autorización |
| **Pagado** | 13 | Nombre propuesto |
| **Turno sacado** | 20 | Lo nombra el PO |
| **Listo para retirar** | 24 | Lo nombra el PO |
| **En camino al laboratorio central** | 27 | Ejemplo del PO |
| **En laboratorio central** | 28 | Nombre propuesto |
| **En viaje a Corea** | 32 | Lo nombra el PO |
| **En el área de bioinformática** | 34 | Lo nombra el PO |
| **En análisis por un bioinformático** | 35 | Lo nombra el PO |
| **Resultado disponible** | 36 | Nombre propuesto |

Mientras espera el presupuesto o la autorización de la **obra social**, el **estudio** sigue en **Creado**. Las bandejas de los escenarios 11 y 18 se arman filtrando por esa condición y no por un estado propio.

**Retrocesos y reingresos:**
- **Cancelación** (22): el **estudio** vuelve al estado previo al turno, **Pagado** o **Autorizado** [supuesto, ver P4].
- **Inasistencia** (23): se reserva un nuevo turno y el **estudio** sigue en **Turno sacado**.
- **Remuestreo** (25): el **estudio** vuelve a **Turno sacado** al reservar el nuevo turno.
- **Rechazo** (19): el **estudio** sigue en **Rechazado** hasta que el **administrativo del laboratorio** registra la nueva respuesta (18).

**Secuencia no definida:** los estados que recorre un reanálisis (P6).

### Otras dimensiones

Son independientes del ciclo de vida.

| Dimensión | Estado | Escenarios |
|---|---|---|
| Prioridad del estudio | **Pompe urgente** | 10, 30 y 35 |
| Muestra de sangre y lote | Comparten los estados logísticos del estudio, desde **Listo para retirar** hasta **En viaje a Corea** | 24 a 32 |
| Cupón de descuento | **Vigente** | 14 y 15 |

---

## Índice

| # | Escenario | Actor principal | Tipo |
|---|---|---|---|
| 1 | Registrarse por autoalta | Médico tratante, Administrativo del laboratorio, Bioinformático | Principal (D1) |
| 2 | Dar de alta a un usuario | Administrador general | Alternativa de diseño (D1) |
| 3 | Activar la cuenta del paciente | Paciente | Principal |
| 4 | Ingresar al sistema | Cualquier rol | Principal (verificación adicional [deseo]) |
| 5 | Dar de alta una patología lisosomal | Gerente médico | Principal |
| 6 | Modificar los síntomas de una patología lisosomal | Gerente médico | Principal |
| 7 | Registrar síntomas con SNOMED | Médico tratante, Gerente médico | Subescenario |
| 8 | Construir el familiograma | Médico tratante, Paciente | Subescenario |
| 9 | Dar de alta al paciente | Médico tratante | Principal |
| 10 | Dar de alta el estudio | Médico tratante | Principal |
| 11 | Emitir el presupuesto | Administrativo del laboratorio | Principal |
| 12 | Elegir la cobertura por obra social | Paciente | Principal |
| 13 | Pagar el estudio de forma particular | Paciente | Principal |
| 14 | Aplicar un cupón de descuento | Paciente | Subescenario de 13 |
| 15 | Generar cupones de descuento | Gerente médico | Principal |
| 16 | Asignar cupones al médico tratante | Gerente médico | Principal |
| 17 | Asignar un cupón al paciente | Médico tratante | Principal |
| 18 | Registrar la autorización de la obra social | Administrativo del laboratorio | Principal |
| 19 | Solicitar la reautorización con una demanda | Paciente, Administrativo del laboratorio | Principal |
| 20 | Sacar turno de extracción | Paciente | Principal |
| 21 | Descargar la orden de extracción y el consentimiento informado | Paciente | Principal |
| 22 | Cancelar el turno de extracción | Paciente | Principal |
| 23 | Registrar una inasistencia y reprogramar el turno | Sistema, Paciente | Principal |
| 24 | Tomar y notificar la muestra de sangre | Paciente, Laboratorio de extracción | Principal |
| 25 | Solicitar el remuestreo | Sistema, Bioinformático | Subescenario de 24 y 36 |
| 26 | Generar y consultar la orden del día | Sistema, Transportista | Principal [deseo] |
| 27 | Retirar muestras en un laboratorio de extracción | Transportista | Principal |
| 28 | Entregar las muestras y armar el lote | Transportista, Sistema | Principal |
| 29 | Solicitar el permiso del Ministerio de Salud | Sistema | Subescenario de 28 y 30 |
| 30 | Cerrar anticipadamente un lote por Pompe urgente | Sistema | Principal |
| 31 | Programar el retiro de un lote con FedEx | Administrativo del laboratorio | Principal |
| 32 | Registrar el retiro de un lote por FedEx | FedEx | Principal |
| 33 | Consultar la ubicación de una muestra en traslado | Administrativo del laboratorio | Principal [deseo] |
| 34 | Cargar los datos crudos de un estudio | Administrativo del laboratorio | Principal |
| 35 | Tomar un estudio para su análisis | Bioinformático | Principal |
| 36 | Registrar variantes y finalizar el análisis | Bioinformático, Sistema | Principal |
| 37 | Consultar el resultado del estudio | Médico tratante | Principal |
| 38 | Descargar el resultado del estudio | Paciente | Principal |
| 39 | Solicitar el reanálisis de un estudio | Médico tratante | Principal |
| 40 | Consultar al chatbot | Paciente | Principal |
| 41 | Consultar avisos pendientes | Cualquier rol | Principal |

---

# A. Acceso y usuarios

## 1. Registrarse por autoalta

**Objetivo:** Que un médico tratante, un administrativo del laboratorio o un bioinformático cree su cuenta con los datos de su rol.

**Contexto:**
- La persona no tiene cuenta y está en la pantalla de ingreso, desde una computadora o un celular.
- Es el mecanismo de alta elegido por el equipo (D1).
- Restricción: la matrícula no se valida contra ningún servicio y las especialidades se eligen de un catálogo estandarizado.
- Restricción [supuesto]: el **transportista** y el **gerente médico** no se registran por autoalta, los da de alta el **administrador general** (escenario 2). Por eso ese rol debe existir aunque los demás roles usen la autoalta.
- Pendiente (P11): si el alta de un **administrativo del laboratorio** o de un **bioinformático** (roles con acceso a datos genéticos) requiere una aprobación posterior.

**Actores:** Médico tratante, Administrativo del laboratorio, Bioinformático (la persona que se registra, con el rol que indique).

**Recursos:** Formulario de registro, catálogo de especialidades, credenciales de acceso.

**Episodios:**
1. La persona solicita registrarse e indica su rol: **médico tratante**, **administrativo del laboratorio** o **bioinformático**.
2. La persona completa su nombre, apellido, teléfono de contacto y mail.
3. Si el rol es **médico tratante**, la persona completa además su matrícula e indica sus especialidades desde el catálogo.
4. La persona define su contraseña y envía el registro.
5. El sistema crea las **credenciales de acceso** y presenta la vista del rol elegido.

**Excepciones:**
- Si el mail ya está registrado, el sistema rechaza el registro.
- Si falta un dato obligatorio, el sistema no permite enviar el registro.

---

## 2. Dar de alta a un usuario

**Objetivo:** Que el administrador general dé de alta a un usuario de cualquier rol, excepto el paciente.

**Contexto:**
- Es la alternativa de diseño al escenario 1 (D1). Si el equipo adopta la autoalta, este escenario sigue siendo el único camino de alta del **transportista** y del **gerente médico** [supuesto].
- El **administrador general** ingresó al sistema y está en el listado de usuarios.
- Restricción: hay un **transportista** por provincia.
- El **paciente** no se da de alta aquí: lo registra el **médico tratante** (escenario 9).

**Actores:** Administrador general.

**Recursos:** Listado de usuarios, formulario de alta, credenciales de acceso.

**Episodios:**
1. El **administrador general** solicita un nuevo usuario desde el listado.
2. El **administrador general** indica el rol: **médico tratante**, **administrativo del laboratorio**, **bioinformático**, **transportista** o **gerente médico**.
3. El **administrador general** completa los datos del rol (para el **transportista**, además, la provincia que cubre).
4. El **administrador general** guarda el alta.
5. El sistema envía las **credenciales de acceso** al mail del nuevo usuario y lo incorpora al listado.

**Excepciones:**
- Si el mail ya existe, el sistema rechaza el alta.
- Si ya hay un **transportista** para la provincia indicada, el sistema rechaza el alta [supuesto].

---

## 3. Activar la cuenta del paciente

**Objetivo:** Que el paciente active su cuenta reemplazando la contraseña inicial.

**Contexto:**
- El **médico tratante** dio de alta al **paciente** (escenario 9) y el **paciente** recibió sus **credenciales de acceso** por mail.
- Restricción: si el **paciente** es menor de edad, las credenciales llegan al mail del padre o la madre, que es quien sigue este escenario.

**Actores:** Paciente.

**Recursos:** Mail con credenciales de acceso, formulario de cambio de contraseña.

**Episodios:**
1. El **paciente** presenta el usuario y la contraseña de sus **credenciales de acceso**.
2. El sistema exige el cambio de contraseña antes de mostrar cualquier otra pantalla.
3. El **paciente** define y repite una nueva contraseña.
4. El sistema activa la cuenta y presenta la vista del **paciente** con su **estudio** y el estado actual.

**Excepciones:**
- Si las dos contraseñas no coinciden, el sistema no las guarda y solicita definirlas de nuevo.

---

## 4. Ingresar al sistema

**Objetivo:** Que un usuario con cuenta acceda a la vista de su rol, con una verificación adicional cuando ingresa desde un dispositivo o una red que no usó antes.

**Contexto:**
- El usuario tiene una cuenta activa. Aplica a todos los roles, desde una computadora o un celular, y se ejemplifica con el **paciente**.
- La seguridad de los datos genéticos es crítica para el PO.
- [deseo] El PO pidió un código por mail cuando se ingresa desde una máquina o una IP nuevas.
- Restricción [supuesto]: tras cinco intentos fallidos consecutivos, el sistema bloquea el ingreso de esa cuenta. La cantidad exacta no surge de la entrevista.
- Pendiente (P12): el criterio para reconocer un dispositivo o una red como nuevos y la forma de restablecer una cuenta bloqueada.

**Actores:** Paciente (o cualquier rol).

**Recursos:** Credenciales de acceso, código de verificación enviado por mail.

**Episodios:**
1. El **paciente** presenta su mail y su contraseña.
2. El sistema reconoce las credenciales y detecta si el dispositivo o la red son nuevos.
3. Si son nuevos, el sistema envía un código de verificación al mail del **paciente**.
4. El **paciente** informa el código recibido.
5. El sistema habilita el acceso y presenta la vista del **paciente**.

**Excepciones:**
- Si las credenciales son incorrectas, el sistema rechaza el ingreso y permite reintentar. No envía el código.
- Si el **paciente** supera los cinco intentos fallidos consecutivos, el sistema bloquea el ingreso de la cuenta y no permite reiniciar el escenario hasta que se la restablezca (P12).
- Si el código es incorrecto o venció, el sistema rechaza el ingreso y permite solicitar uno nuevo.

---

# B. Configuración médica

## 5. Dar de alta una patología lisosomal

**Objetivo:** Que el gerente médico registre una patología lisosomal con sus síntomas, para usarla como diagnóstico presuntivo.

**Contexto:**
- El **gerente médico** ingresó al sistema y está en la sección de patologías.
- El laboratorio trabaja con cinco **patologías lisosomales**: enfermedad de Fabry, enfermedad de Pompe, mucopolisacaridosis tipo 1, enfermedad de Gaucher y ASMD.
- Restricción: los **genes** de cada **patología lisosomal** no se cargan aquí, los mantiene la **Bioinformática API**.

**Actores:** Gerente médico.

**Recursos:** Formulario de patología, buscador de síntomas.

**Episodios:**
1. El **gerente médico** registra el nombre de una nueva **patología lisosomal**.
2. El **gerente médico** define el **síntoma cardinal** mediante REGISTRAR SÍNTOMAS CON SNOMED (7).
3. El **gerente médico** agrega los **síntomas secundarios** mediante REGISTRAR SÍNTOMAS CON SNOMED (7).
4. El **gerente médico** guarda el alta de la patología.
5. El sistema deja la **patología lisosomal** disponible como **diagnóstico presuntivo**.

**Excepciones:**
- Si la **patología lisosomal** ya existe, el sistema lo informa y no la duplica.

---

## 6. Modificar los síntomas de una patología lisosomal

**Objetivo:** Que el gerente médico actualice el síntoma cardinal o los síntomas secundarios de una patología existente.

**Contexto:**
- La **patología lisosomal** ya existe.
- Restricción [supuesto]: el cambio rige para las próximas altas de **pacientes**. No modifica a los **pacientes** ya registrados.
- Pendiente (P13): la entrevista no define qué ocurre con los **pacientes** ya registrados.

**Actores:** Gerente médico.

**Recursos:** Listado de patologías, buscador de síntomas.

**Episodios:**
1. El **gerente médico** abre una **patología lisosomal** del listado y solicita editarla.
2. Si corresponde, el **gerente médico** reemplaza el **síntoma cardinal** mediante REGISTRAR SÍNTOMAS CON SNOMED (7).
3. Si corresponde, el **gerente médico** agrega o quita **síntomas secundarios**.
4. El **gerente médico** guarda los cambios.

**Excepciones:** Ninguna identificada.

---

# C. Consulta médica

## 7. Registrar síntomas con SNOMED

**Objetivo:** Que el actor cargue síntomas codificados con SNOMED, sin texto libre.

**Contexto:**
- Subescenario invocado desde los escenarios 5, 6, 8 y 9.
- Cuando se invoca para el **síntoma cardinal**, se carga un solo **síntoma**. En los demás casos, se cargan todos los que haga falta.

**Actores:** Médico tratante o Gerente médico.

**Recursos:** Buscador conectado a **SNOMED**.

**Episodios:**
1. El actor escribe al menos tres letras del **síntoma** en el buscador.
2. El sistema consulta **SNOMED** y presenta los términos que coinciden.
3. El actor incorpora el término buscado.
4. El sistema agrega el **síntoma** al conjunto que se está cargando y permite repetir la búsqueda.

**Excepciones:**
- Si **SNOMED** no devuelve coincidencias, el sistema informa que no hay resultados y no admite texto libre.

---

## 8. Construir el familiograma

**Objetivo:** Que el médico tratante registre a los familiares del paciente y obtenga el familiograma en PDF.

**Contexto:**
- Subescenario opcional del escenario 9, en la misma consulta.
- Restricción: el **familiograma** es el único dato del alta que puede quedar vacío.

**Actores:** Médico tratante, Paciente.

**Recursos:** Formulario de familiar, módulo externo de familiograma.

**Episodios:**
1. El **paciente** informa al **médico tratante** quiénes son sus **familiares** y qué antecedentes tienen [supuesto, a partir de que el PO pregunta por la familia en la misma consulta].
2. El **médico tratante** registra, de cada **familiar**, el parentesco, el nombre y si ya tiene diagnóstico de alguna **patología lisosomal**.
3. El **médico tratante** carga los **síntomas** de cada **familiar** mediante REGISTRAR SÍNTOMAS CON SNOMED (7). Los episodios 2 y 3 se repiten por cada **familiar**.
4. El **médico tratante** solicita generar el **familiograma**.
5. El sistema envía los parentescos al módulo de familiograma, recibe el **familiograma** en PDF y lo asocia al **paciente**.

**Excepciones:**
- Si el **paciente** no quiere o no puede informar sobre su familia, el **médico tratante** omite este subescenario y el **familiograma** queda vacío.
- Si el módulo de familiograma no devuelve el PDF, el sistema lo informa, no bloquea el alta del **paciente** y el **familiograma** queda vacío [supuesto].

---

## 9. Dar de alta al paciente

**Objetivo:** Que el médico tratante registre al paciente durante la consulta, con su información clínica verificada.

**Contexto:**
- El **médico tratante** ingresó al sistema y está en consulta con el **paciente**, que no existe en el sistema.
- Restricción: todos los datos son obligatorios, salvo el **familiograma**.
- Restricción: según la **regla de correspondencia clínica**, el **paciente** debe presentar el **síntoma cardinal** de la **patología lisosomal** sospechada o dos **síntomas secundarios** de ella.
- Restricción: si el **paciente** es menor de edad, el procedimiento es el mismo. Cambian el mail asociado (el de los padres) y quién firma el **consentimiento informado**.
- Pendiente (P1): si la **regla de correspondencia clínica** se aplica a una **sospecha familiar**, donde el **paciente** puede no tener **síntomas** aunque la lista de **síntomas** sea obligatoria.

**Actores:** Médico tratante.

**Recursos:** Formulario de alta de paciente, catálogo de patologías, micrófono del dispositivo [deseo].

**Episodios:**
1. El **médico tratante** registra los datos personales del **paciente**: DNI, nombre, apellido, fecha de nacimiento, teléfono y mail (el de los padres, si es menor de edad).
2. El **médico tratante** indica los **diagnósticos presuntivos** (uno o más) y el **tipo de sospecha** (**sospecha clínica** o **sospecha familiar**).
3. El **médico tratante** redacta o dicta [deseo] el **resumen de historia clínica** y carga los **síntomas** mediante REGISTRAR SÍNTOMAS CON SNOMED (7).
4. Si el **paciente** informa sobre su familia, el **médico tratante** registra a los **familiares** mediante CONSTRUIR EL FAMILIOGRAMA (8).
5. El sistema **verifica la correspondencia clínica**, da de alta al **paciente** y le envía sus **credenciales de acceso** por mail.

**Excepciones:**
- Si en una **sospecha clínica** no se cumple la **regla de correspondencia clínica**, el sistema bloquea el alta e indica qué falta.
- Si el DNI ya existe, el sistema presenta al **paciente** existente y se continúa con DAR DE ALTA EL ESTUDIO (10).
- Si el dictado no está disponible, el **médico tratante** escribe el **resumen de historia clínica**.

---

## 10. Dar de alta el estudio

**Objetivo:** Que el médico tratante solicite el estudio de un paciente, con la lista de genes a analizar.

**Contexto:**
- El **médico tratante** ingresó al sistema.
- Restricción: todo **estudio** lo solicita un **médico tratante**.
- Restricción: pueden sospecharse varias **patologías lisosomales** a la vez, y se analizan en el mismo **estudio**.
- Restricción: la **lista de genes** depende de las **patologías lisosomales** sospechadas y la devuelve la **Bioinformática API**. El **médico tratante** puede agregar **genes** manualmente.
- Pendiente (P15): si los **genes** de los **hallazgos secundarios** cuentan para la tarifa del **presupuesto** (500 USD hasta cinco **genes**).

**Actores:** Médico tratante, Sistema.

**Recursos:** Ficha del paciente, Bioinformática API, buscador de genes.

**Episodios:**
1. El **médico tratante** busca al **paciente** por DNI y, si no existe, lo registra mediante DAR DE ALTA AL PACIENTE (9).
2. El **médico tratante** indica las **patologías lisosomales** sospechadas y si se evalúan **hallazgos secundarios**.
3. El sistema obtiene de la **Bioinformática API** la **lista de genes** de esas patologías y, si corresponde, la de los **hallazgos secundarios**.
4. El **médico tratante** agrega **genes** desde el buscador, si lo considera necesario, y solicita el **estudio**.
5. El sistema registra el **estudio** en estado **Creado** y, si entre las patologías sospechadas está la enfermedad de Pompe y el **paciente** tiene menos de cuatro meses, le asigna la prioridad **Pompe urgente**.

**Excepciones:**
- Si la **Bioinformática API** no responde, el sistema lo informa y no permite solicitar el **estudio** [supuesto].

---

# D. Presupuesto y pago

## 11. Emitir el presupuesto

**Objetivo:** Que el administrativo del laboratorio emita el presupuesto del estudio para que el paciente lo vea.

**Contexto:**
- Hay **estudios** en estado **Creado** sin **presupuesto**.
- Restricción: la tarifa es fija y no editable (500 USD hasta cinco **genes** y 30 USD por cada **gen** adicional) e incluye la extracción y el **turno de extracción**.
- [supuesto] El **paciente** recibe un **aviso** cuando se publica el **presupuesto**.

**Actores:** Administrativo del laboratorio.

**Recursos:** Bandeja de estudios, lista de genes del estudio.

**Episodios:**
1. El **administrativo del laboratorio** abre la bandeja de **estudios** en estado **Creado** sin **presupuesto**.
2. El **administrativo del laboratorio** consulta la **lista de genes** de un **estudio**.
3. El sistema calcula el importe aplicando la tarifa fija a la cantidad de **genes**.
4. El **administrativo del laboratorio** emite el **presupuesto**.
5. El sistema publica el **presupuesto** en la vista del **paciente** y le envía un **aviso**.

**Excepciones:** Ninguna identificada.

---

## 12. Elegir la cobertura por obra social

**Objetivo:** Que el paciente indique que su obra social cubrirá el estudio, para que se inicie la autorización.

**Contexto:**
- El **presupuesto** está emitido.
- Restricción: la lista de **obras sociales** y sus porcentajes de cobertura la provee un módulo externo.
- Pendiente (P14): la entrevista no define cómo se liquida la diferencia a cargo del **paciente** cuando la **obra social** cubre solo un porcentaje.

**Actores:** Paciente.

**Recursos:** Presupuesto, listado de obras sociales.

**Episodios:**
1. El **paciente** consulta el **presupuesto** de su **estudio**.
2. El **paciente** opta por la cobertura de **obra social**.
3. El sistema presenta la lista de **obras sociales**.
4. El **paciente** indica la suya.
5. El sistema muestra el porcentaje de cobertura de esa **obra social** y deja el **estudio** a la espera de la **autorización de obra social**.

**Excepciones:**
- Si la **obra social** del **paciente** no figura en la lista, solo queda disponible el **pago particular** (escenario 13) [supuesto].

---

## 13. Pagar el estudio de forma particular

**Objetivo:** Que el paciente abone el estudio y quede habilitado para sacar turno.

**Contexto:**
- El **presupuesto** está emitido.
- Restricción: el pago es simulado, pero se asienta en el **registro financiero**. A futuro se integrará Mercado Pago.

**Actores:** Paciente.

**Recursos:** Presupuesto, pantalla de pago simulado, registro financiero.

**Episodios:**
1. El **paciente** opta por el **pago particular** de su **presupuesto**.
2. El sistema informa el importe a abonar.
3. El **paciente** aplica, si tiene uno, un descuento mediante APLICAR UN CUPÓN DE DESCUENTO (14).
4. El **paciente** abona el importe.
5. El sistema asienta el pago en el **registro financiero**, informa el uso del **cupón de descuento** si hubo uno, pasa el **estudio** a **Pagado** y avisa al **paciente** que ya puede sacar su turno.

**Excepciones:**
- Si el **paciente** abandona antes de abonar, el **estudio** sigue en **Creado** y no se registra ninguna operación.

---

## 14. Aplicar un cupón de descuento

**Objetivo:** Que el paciente reduzca el importe del pago particular con un cupón de descuento vigente.

**Contexto:**
- Subescenario del escenario 13, que se ejecuta antes de abonar.
- El **paciente** tiene un **cupón de descuento** que le asignó su **médico tratante** (escenario 17).
- Restricción: la vigencia del **cupón de descuento** la determina el módulo externo de cupones. El uso del cupón se informa a ese módulo al concretarse el pago (episodio 5 del escenario 13).

**Actores:** Paciente.

**Recursos:** PDF del cupón de descuento con QR (o código numérico), módulo de cupones.

**Episodios:**
1. El **paciente** solicita aplicar un cupón.
2. El **paciente** adjunta el PDF del **cupón de descuento** o informa su código.
3. El sistema consulta al módulo de cupones si el **cupón de descuento** está **Vigente**.
4. El sistema muestra el descuento y el nuevo importe.

**Excepciones:**
- Si el **cupón de descuento** no está **Vigente**, el sistema muestra el motivo y mantiene el importe original.

---

## 15. Generar cupones de descuento

**Objetivo:** Que el gerente médico cree cupones con un descuento determinado.

**Contexto:**
- El **gerente médico** ingresó al sistema y está en la sección de cupones.

**Actores:** Gerente médico.

**Recursos:** Formulario de cupones, módulo de cupones.

**Episodios:**
1. El **gerente médico** define el descuento y la cantidad de **cupones de descuento**.
2. El **gerente médico** solicita generarlos.
3. El sistema pide al módulo de cupones la creación de los **cupones de descuento**.
4. El sistema presenta los **cupones de descuento** generados en estado **Vigente**, con su PDF.

**Excepciones:**
- Si el módulo de cupones rechaza la solicitud, el sistema no muestra cupones nuevos e informa el error.

---

## 16. Asignar cupones al médico tratante

**Objetivo:** Que el gerente médico entregue cupones a un médico tratante.

**Contexto:**
- Hay **cupones de descuento** **Vigentes** sin asignar.
- Restricción: solo puede recibir cupones un **médico tratante** registrado.

**Actores:** Gerente médico.

**Recursos:** Listado de cupones, buscador de médicos.

**Episodios:**
1. El **gerente médico** marca uno o más **cupones de descuento** **Vigentes** para entregar.
2. El **gerente médico** busca al **médico tratante** por nombre o matrícula.
3. El **gerente médico** asigna los cupones al **médico tratante**.
4. El sistema agrega los **cupones de descuento** a la sección de cupones del **médico tratante** y le envía un **aviso**.

**Excepciones:** Ninguna identificada.

---

## 17. Asignar un cupón al paciente

**Objetivo:** Que el médico tratante entregue un cupón de descuento al paciente que elija.

**Contexto:**
- El **médico tratante** tiene **cupones de descuento** asignados.
- Restricción: los cupones son limitados, y el **médico tratante** decide a quién se los da.

**Actores:** Médico tratante.

**Recursos:** Sección de cupones del médico, ficha del paciente.

**Episodios:**
1. El **médico tratante** abre su sección de cupones y consulta los **cupones de descuento** disponibles.
2. El **médico tratante** indica el cupón que quiere entregar.
3. El **médico tratante** busca al **paciente** y le asigna el cupón.
4. El sistema descuenta el cupón de los disponibles del **médico tratante** y lo publica en la vista del **paciente**.

**Excepciones:**
- Si el **médico tratante** no tiene cupones disponibles, el sistema deshabilita la asignación.

---

## 18. Registrar la autorización de la obra social

**Objetivo:** Que el administrativo del laboratorio registre la respuesta de la obra social para que el estudio pueda avanzar.

**Contexto:**
- El **paciente** eligió la cobertura por **obra social** (escenario 12), o el **estudio** está **Rechazado** y tiene una **demanda** asociada (escenario 19).
- Restricción: el **administrativo del laboratorio** obtiene la respuesta por teléfono, fuera del sistema. No hay consulta automática a la **obra social**.
- Restricción: un **estudio** **Autorizado** se considera autorizado y pagado.
- Pendiente (P14): qué ocurre con la diferencia a cargo del **paciente** si la cobertura es parcial.

**Actores:** Administrativo del laboratorio, Obra social (actor externo, fuera del sistema).

**Recursos:** Bandeja de autorizaciones pendientes, registro financiero.

**Episodios:**
1. El **administrativo del laboratorio** abre la bandeja de **estudios** con **autorización de obra social** pendiente.
2. El **administrativo del laboratorio** gestiona por teléfono la autorización con la **obra social**.
3. El **administrativo del laboratorio** registra la respuesta: "Autorizado".
4. El sistema pasa el **estudio** a **Autorizado** y asienta la operación en el **registro financiero**.
5. El sistema envía un **aviso** al **paciente** y habilita la reserva del **turno de extracción**.

**Excepciones:**
- Si la **obra social** rechaza el **estudio**, el **administrativo del laboratorio** registra "Rechazado" junto con el motivo. El **estudio** pasa a **Rechazado** y se avisa al **paciente**, que puede continuar con SOLICITAR LA REAUTORIZACIÓN CON UNA DEMANDA (19).
- Pendiente (P8): si, tras un rechazo, el **paciente** puede optar por el **pago particular**.

---

## 19. Solicitar la reautorización con una demanda

**Objetivo:** Que el paciente presente una decisión judicial favorable para destrabar un estudio rechazado.

**Contexto:**
- El **estudio** está en estado **Rechazado** y el **paciente** obtuvo un fallo favorable.
- Restricción: el **estudio** sigue en **Rechazado** hasta que el **administrativo del laboratorio** registra la nueva respuesta.

**Actores:** Paciente, Administrativo del laboratorio.

**Recursos:** PDF de la demanda, motivo del rechazo.

**Episodios:**
1. El **paciente** consulta el motivo del rechazo de su **estudio**.
2. El **paciente** solicita la reautorización y adjunta el PDF de la **demanda**.
3. El sistema asocia la **demanda** al **estudio** y envía un **aviso** al **administrativo del laboratorio** [supuesto].
4. El **administrativo del laboratorio** descarga la **demanda** y registra la nueva respuesta mediante REGISTRAR LA AUTORIZACIÓN DE LA OBRA SOCIAL (18).

**Excepciones:**
- Si el archivo no es un PDF, el sistema rechaza la carga.

---

# E. Turno y extracción

## 20. Sacar turno de extracción

**Objetivo:** Que el paciente reserve un turno en el laboratorio de extracción que le quede más cerca.

**Contexto:**
- El **estudio** está en estado **Pagado** o **Autorizado**, o el **paciente** tiene habilitada una nueva reserva por cancelación (22), inasistencia (23) o remuestreo (25).
- Restricción: cada **laboratorio de extracción** tiene su propio turnero, con un **turno de extracción** cada 15 minutos y para una persona. Hay turnos de lunes a viernes, de 9 a 18, sin feriados.
- Restricción [supuesto]: el sistema genera los turnos libres de cada **laboratorio de extracción** con esa regla, porque los laboratorios no operan en la plataforma.
- Restricción: el turno está incluido en el **presupuesto**.

**Actores:** Paciente.

**Recursos:** Mapa de laboratorios de extracción, turneros.

**Episodios:**
1. El **paciente** solicita un turno para su **estudio**.
2. El sistema presenta en un mapa los **laboratorios de extracción**.
3. El **paciente** define el **laboratorio de extracción** y uno de sus **turnos de extracción** libres.
4. El sistema reserva el turno, pasa el **estudio** a **Turno sacado** y programa el recordatorio por mail.
5. El sistema publica en la plataforma la **orden de extracción** y el **consentimiento informado**.

**Excepciones:**
- Si el turno elegido se ocupa antes de reservarlo, el sistema lo informa y presenta los turnos libres actualizados.
- Si el **laboratorio de extracción** no tiene turnos libres, el sistema lo informa y el **paciente** puede elegir otro [supuesto].

---

## 21. Descargar la orden de extracción y el consentimiento informado

**Objetivo:** Que el paciente obtenga los documentos para asistir al turno.

**Contexto:**
- El **estudio** está en estado **Turno sacado** y ambos documentos están publicados en la plataforma desde la reserva (escenario 20).
- Restricción: el **consentimiento informado** se imprime, completa, firma y entrega en papel. No se sube al sistema.
- Restricción: si el **paciente** es menor de edad, el **consentimiento informado** lo firman sus padres.

**Actores:** Paciente.

**Recursos:** Orden de extracción, plantilla del consentimiento informado.

**Episodios:**
1. El **paciente** abre su **estudio** en estado **Turno sacado**.
2. El **paciente** consulta la **orden de extracción**, con la fecha, el horario, el **laboratorio de extracción** y las indicaciones previas.
3. El **paciente** descarga el **consentimiento informado** para imprimirlo.
4. El sistema indica que el **consentimiento informado** firmado se entrega en el **laboratorio de extracción**.

**Excepciones:** Ninguna identificada.

---

## 22. Cancelar el turno de extracción

**Objetivo:** Que el paciente libere de forma voluntaria un turno que no va a usar.

**Contexto:**
- El **estudio** está en estado **Turno sacado**.
- Restricción: la cancelación no tiene costo ni penalidad, y no cuenta como **inasistencia**.
- Restricción [supuesto]: el **estudio** vuelve al estado previo al turno (**Pagado** o **Autorizado**), de modo que se pueda sacar uno nuevo (P4).
- Restricción [supuesto]: solo se cancela un turno cuya hora todavía no pasó.

**Actores:** Paciente.

**Recursos:** Detalle del turno de extracción.

**Episodios:**
1. El **paciente** abre el detalle de su **turno de extracción**.
2. El **paciente** solicita cancelar el turno.
3. El sistema libera el **turno de extracción** en el turnero del **laboratorio de extracción** y anula su recordatorio.
4. El sistema devuelve el **estudio** al estado previo al turno.
5. El sistema habilita una nueva reserva mediante SACAR TURNO DE EXTRACCIÓN (20).

**Excepciones:**
- Si la hora del turno ya pasó, el sistema no permite cancelarlo y lo trata como **inasistencia** (escenario 23).

---

## 23. Registrar una inasistencia y reprogramar el turno

**Objetivo:** Que, ante una inasistencia, el paciente pueda volver a reservar un turno.

**Contexto:**
- El **paciente** no asistió a su **turno de extracción**.
- Restricción: el límite de **inasistencias** es de 5.
- Pendiente (P3): quién y cómo registra la **inasistencia**.
- Pendiente (P2): la consecuencia de superar el límite. El PO propuso que se pierda el pago, pero lo calificó de "bastante violento" y no quedó como regla.

**Actores:** Sistema, Paciente.

**Recursos:** Contador de inasistencias, avisos, turneros de los laboratorios de extracción.

**Episodios:**
1. El sistema registra la **inasistencia** e incrementa el contador del **estudio**.
2. El sistema envía al **paciente** un **aviso** con la cantidad de **inasistencias** acumuladas.
3. El **paciente** abre su **estudio** y solicita un nuevo turno.
4. El **paciente** reserva el nuevo turno mediante SACAR TURNO DE EXTRACCIÓN (20), y el **estudio** sigue en **Turno sacado**.

**Excepciones:**
- Si el **paciente** llega a 5 **inasistencias**, el sistema lo informa. No se aplica ningún bloqueo ni pérdida hasta que se resuelva P2.

---

## 24. Tomar y notificar la muestra de sangre

**Objetivo:** Que se tome la muestra de sangre y que el laboratorio central reciba automáticamente la notificación para su posterior retiro.

**Contexto:**
- El **paciente** asiste a su **turno de extracción**.
- Restricción: el **laboratorio de extracción** no opera en la plataforma, y la recepción de la notificación en el **laboratorio central** no debe depender de una persona.
- Restricción: la **muestra de sangre** debe tener un volumen mínimo de 2 ml para continuar el proceso.
- [deseo] La notificación por Telegram con un bot es una propuesta del PO, sujeta al costo.
- Restricción [supuesto]: el volumen viaja en la propia notificación (P7).

**Actores:** Paciente, Laboratorio de extracción, Sistema.

**Recursos:** Consentimiento informado firmado, muestra de sangre, número del laboratorio central.

**Episodios:**
1. El **paciente** entrega el **consentimiento informado** firmado en el **laboratorio de extracción**.
2. El **laboratorio de extracción** toma la **muestra de sangre** y registra su volumen en mililitros.
3. El **laboratorio de extracción** notifica la toma al **laboratorio central**, con los datos que identifican el **estudio** y el volumen de la muestra.
4. El sistema recibe la notificación sin intervención de personas y registra la **muestra de sangre** en el **estudio**.
5. Si el volumen alcanza los 2 ml, el sistema pasa el **estudio** a **Listo para retirar** y lo incluye entre las muestras por retirar.

**Excepciones:**
- Si la **muestra de sangre** tiene menos de 2 ml, no se habilita su retiro y se continúa con SOLICITAR EL REMUESTREO (25).

---

## 25. Solicitar el remuestreo

**Objetivo:** Que el paciente vuelva a dar una muestra, sin costo, cuando la anterior no sirve para el estudio.

**Contexto:**
- Subescenario invocado desde el escenario 24 (volumen menor a 2 ml) y desde el escenario 36 (**ADN** insuficiente).
- Restricción: es el mismo **estudio**, sin costo para el **paciente**, y conserva el historial del **estudio** y de la **muestra de sangre** anterior.
- Restricción [supuesto]: el **ADN** desnaturalizado lo detecta el **bioinformático** al analizar el **estudio**, y el volumen insuficiente lo detecta el sistema al recibir la notificación.
- Pendiente (P7): confirmar con el PO cómo llega el volumen al sistema y quién detecta el **ADN** insuficiente.

**Actores:** Sistema, Bioinformático, Paciente.

**Recursos:** Detalle del estudio, avisos.

**Episodios:**
1. El sistema registra en el **estudio** el motivo del remuestreo: volumen menor a 2 ml o **ADN** desnaturalizado, este último indicado por el **bioinformático**.
2. El sistema envía un **aviso** al **médico tratante** y al **paciente**.
3. El sistema habilita al **paciente** para sacar un nuevo turno, sin nuevo cobro y sin crear un nuevo **estudio**.
4. El **paciente** reserva el turno mediante SACAR TURNO DE EXTRACCIÓN (20), y el **estudio** pasa a **Turno sacado**.

**Excepciones:**
- Si el **paciente** no reserva el nuevo turno, el **estudio** queda detenido y el **aviso** sigue pendiente en su vista.

---

# F. Logística

## 26. Generar y consultar la orden del día

**Objetivo:** Que el transportista conozca al comenzar la jornada el recorrido que debe seguir y cuántas muestras retira en cada parada.

**Contexto:**
- Es un día hábil por la mañana y hay **estudios** **Listos para retirar** en la provincia del **transportista**.
- Restricción: el recorrido es fijo y el **transportista** no puede reordenarlo.
- [deseo] La app del **transportista** es una propuesta del PO, sujeta al costo.
- Pendiente (P17): la contratación del módulo de optimización de recorridos no está confirmada.

**Actores:** Sistema, Transportista.

**Recursos:** App del transportista [deseo], módulo de optimización de recorridos.

**Episodios:**
1. El sistema envía al módulo de optimización las direcciones de los **laboratorios de extracción** con **muestras de sangre** por retirar en la provincia, y recibe el orden del recorrido.
2. El sistema presenta al **transportista** su **orden del día**, con los **laboratorios de extracción** numerados según el recorrido.
3. El **transportista** consulta cuántas **muestras de sangre** debe retirar en cada parada.

**Excepciones:**
- En fines de semana y feriados no se genera **orden del día**.
- Si no hay muestras para retirar en la provincia, el sistema informa que no hay recorrido para esa jornada.

---

## 27. Retirar muestras en un laboratorio de extracción

**Objetivo:** Que el transportista retire las muestras de una parada y registre que ya las lleva.

**Contexto:**
- El **transportista** llegó a un **laboratorio de extracción** de su **orden del día**.
- Restricción: las paradas se recorren en el orden fijado.
- Restricción: se asume que una muestra retirada llega al **laboratorio central**. Los incidentes de transporte quedan fuera del alcance del sistema.

**Actores:** Transportista.

**Recursos:** App del transportista [deseo], orden del día.

**Episodios:**
1. El **transportista** identifica en su **orden del día** la parada del **laboratorio de extracción** en el que está.
2. El **transportista** retira las **muestras de sangre** pendientes de esa parada.
3. El **transportista** registra el retiro de las muestras.
4. El sistema pasa todas las **muestras de sangre** de ese **laboratorio de extracción** a **En camino al laboratorio central** y marca la parada como completada.
5. El sistema presenta la siguiente parada del recorrido, si la hay.

**Excepciones:**
- Si el **transportista** intenta registrar una parada fuera del orden, el sistema no lo permite y mantiene la parada pendiente.

---

## 28. Entregar las muestras y armar el lote

**Objetivo:** Que el transportista registre la llegada al laboratorio central y el sistema arme los lotes automáticamente.

**Contexto:**
- El **transportista** completó su recorrido y llegó al **laboratorio central** con las **muestras de sangre** retiradas.
- Restricción: el **lote** estándar es de 10 **estudios**, se arma sin intervención humana y por orden de llegada.
- Restricción: un **lote** incompleto queda abierto, aunque termine el día, hasta completar los 10 **estudios**. La única excepción es el cierre anticipado por **Pompe urgente**.

**Actores:** Transportista, Sistema.

**Recursos:** App del transportista [deseo], registro de muestras retiradas, lote abierto.

**Episodios:**
1. El **transportista** registra su llegada al **laboratorio central** con todas las **muestras de sangre** que retiró.
2. El sistema pasa las **muestras de sangre** entregadas y sus **estudios** a **En laboratorio central**.
3. El sistema incorpora cada **estudio** al **lote** abierto, por orden de llegada.
4. Al llegar a 10 **estudios**, el sistema cierra el **lote** y abre uno nuevo para los restantes.
5. El sistema solicita la autorización del **lote** cerrado mediante SOLICITAR EL PERMISO DEL MINISTERIO DE SALUD (29).

**Excepciones:**
- Si entra un **estudio** con **Pompe urgente**, se continúa con CERRAR ANTICIPADAMENTE UN LOTE POR POMPE URGENTE (30).

---

## 29. Solicitar el permiso del Ministerio de Salud

**Objetivo:** Que el lote cerrado obtenga la autorización para que sus muestras salgan del país.

**Contexto:**
- Subescenario de los escenarios 28 y 30: se aplica a todo **lote** cerrado, incluido el urgente.
- Restricción: ningún **lote** viaja a **Corea** sin el **permiso del Ministerio de Salud**.

**Actores:** Sistema, API del Ministerio de Salud (actor externo).

**Recursos:** Lote cerrado, CSV de pacientes, permiso del Ministerio de Salud.

**Episodios:**
1. El sistema genera el **CSV de pacientes** con los **estudios** del **lote** cerrado.
2. El sistema envía el **CSV de pacientes** a la API del Ministerio de Salud.
3. La API del Ministerio de Salud devuelve el **permiso del Ministerio de Salud** en PDF.
4. El sistema asocia el permiso y el CSV a cada **estudio** del **lote**.
5. El sistema deja el permiso disponible para el **administrativo del laboratorio** y habilita el **lote** para PROGRAMAR EL RETIRO DE UN LOTE CON FEDEX (31).

**Excepciones:**
- Si no se recibe el **permiso del Ministerio de Salud**, el sistema informa que el **lote** no está autorizado y no permite programar su retiro.

---

## 30. Cerrar anticipadamente un lote por Pompe urgente

**Objetivo:** Que un estudio con Pompe urgente viaje sin esperar a que se complete el lote.

**Contexto:**
- Llegó al **laboratorio central** un **estudio** con prioridad **Pompe urgente**, correspondiente a una sospecha de enfermedad de Pompe en un **paciente** menor de cuatro meses.
- Restricción: es la única excepción a la capacidad de 10 **estudios**.
- Restricción: el costo no cambia y el **permiso del Ministerio de Salud** sigue siendo obligatorio.

**Actores:** Sistema.

**Recursos:** Lote abierto, estudio con prioridad Pompe urgente, alerta de urgencia.

**Episodios:**
1. El sistema incorpora el **estudio** con **Pompe urgente** al **lote** abierto.
2. El sistema cierra ese **lote** con todos los **estudios** que contiene, aunque sean menos de 10.
3. El sistema abre un nuevo **lote** para las siguientes **muestras de sangre**.
4. El sistema solicita la autorización mediante SOLICITAR EL PERMISO DEL MINISTERIO DE SALUD (29).
5. El sistema alerta al **administrativo del laboratorio** que hay un **lote** urgente para PROGRAMAR EL RETIRO DE UN LOTE CON FEDEX (31) [supuesto].

**Excepciones:**
- Si llega otra **muestra de sangre** después de que el **lote** pasó a **En viaje a Corea**, se incorpora al siguiente **lote**.

---

## 31. Programar el retiro de un lote con FedEx

**Objetivo:** Que el administrativo del laboratorio agende con FedEx el retiro de un lote autorizado.

**Contexto:**
- El **lote** está cerrado y tiene asociado el **permiso del Ministerio de Salud**.
- Restricción: cada **lote** es un paquete independiente con su propia URL.
- Restricción: los retiros se programan en días hábiles, de 9 a 18, sin feriados.

**Actores:** Administrativo del laboratorio, FedEx.

**Recursos:** Detalle del lote, permiso del Ministerio de Salud, URL del lote, módulo de FedEx.

**Episodios:**
1. El **administrativo del laboratorio** abre el **lote** autorizado y solicita programar su retiro.
2. El **administrativo del laboratorio** fija el día y la hora del retiro dentro de los horarios permitidos.
3. El sistema envía al módulo de **FedEx** el día, la hora y la URL del **lote**.
4. **FedEx** confirma la programación del retiro.
5. El sistema registra la programación y presenta el **lote** con el día y la hora acordados.

**Excepciones:**
- Si **FedEx** no confirma la programación, el sistema informa que el retiro no pudo programarse y el **lote** sigue sin retiro programado.
- El sistema no ofrece horarios fuera de 9 a 18, ni fines de semana ni feriados.

---

## 32. Registrar el retiro de un lote por FedEx

**Objetivo:** Que el lote y sus estudios cambien de estado cuando FedEx retira el paquete.

**Contexto:**
- El **lote** está cerrado, cuenta con el **permiso del Ministerio de Salud** y tiene su retiro programado. Llegó la hora acordada.
- Restricción: el retiro se simula con la llamada de **FedEx** a la URL del **lote**, por decisión del PO.

**Actores:** FedEx, Sistema.

**Recursos:** URL del lote, programación del retiro, estudios asociados.

**Episodios:**
1. **FedEx** llama a la URL del **lote** a la hora programada.
2. El sistema identifica el **lote** y registra que fue retirado.
3. El sistema pasa el **lote** y todos sus **estudios** a **En viaje a Corea**.
4. El sistema sella el **lote**, que ya no admite **muestras de sangre**, y refleja el nuevo estado en la vista del **administrativo del laboratorio**.

**Excepciones:**
- Si la llamada no llega, el **lote** mantiene su estado y el retiro sigue programado.

---

## 33. Consultar la ubicación de una muestra en traslado

**Objetivo:** Que el administrativo del laboratorio sepa por dónde viene la muestra de un paciente.

**Contexto:**
- La **muestra de sangre** fue retirada y está **En camino al laboratorio central**, a cargo de un **transportista**.
- [deseo] Lo pidió el PO, pero falta especificar la integración de geolocalización (P9).

**Actores:** Administrativo del laboratorio.

**Recursos:** Buscador de estudios, información de ubicación del transportista, mapa.

**Episodios:**
1. El **administrativo del laboratorio** busca el **estudio** por nombre o DNI del **paciente**.
2. El sistema identifica la **muestra de sangre** en traslado y el **transportista** responsable.
3. El **administrativo del laboratorio** solicita conocer la ubicación de la muestra.
4. El sistema muestra en el mapa la ubicación disponible del **transportista**.

**Excepciones:**
- Si la muestra todavía no fue retirada, el sistema muestra el **laboratorio de extracción** donde espera.
- Si no se dispone de la ubicación del **transportista**, el sistema informa que no es posible mostrarla.

---

# G. Bioinformática y resultados

## 34. Cargar los datos crudos de un estudio

**Objetivo:** Que el administrativo del laboratorio cargue los datos crudos recibidos de Corea para que el estudio quede disponible para su análisis.

**Contexto:**
- El **estudio** está **En viaje a Corea** y el **administrativo del laboratorio** recibió sus **datos crudos** por mail, fuera del sistema.
- Restricción: la carga es manual y por **estudio**. El **lote** se disuelve en este punto y cada **estudio** vuelve a ser individual.

**Actores:** Administrativo del laboratorio, Sistema.

**Recursos:** Archivo de datos crudos, detalle del estudio.

**Episodios:**
1. El **administrativo del laboratorio** busca el **estudio** en estado **En viaje a Corea** que corresponde a los **datos crudos** recibidos.
2. El **administrativo del laboratorio** adjunta el archivo de **datos crudos**.
3. El sistema asocia los **datos crudos** al **estudio** y lo pasa a **En el área de bioinformática**.
4. El sistema envía un **aviso** por mail a todos los **bioinformáticos**.

**Excepciones:**
- Si el archivo está vacío, el sistema rechaza la carga [supuesto].

---

## 35. Tomar un estudio para su análisis

**Objetivo:** Que un bioinformático tome un estudio disponible y que los demás vean que ya está asignado.

**Contexto:**
- El **bioinformático** ingresó al sistema y hay **estudios** **En el área de bioinformática**.
- Restricción: los **estudios** con **Pompe urgente** aparecen primero. El resto, por orden de llegada.

**Actores:** Bioinformático, Sistema.

**Recursos:** Lista de tareas de bioinformática, lista de genes.

**Episodios:**
1. El **bioinformático** consulta la lista de **estudios** disponibles.
2. El **bioinformático** revisa la **lista de genes** de un **estudio**.
3. El **bioinformático** solicita tomar el **estudio**.
4. El sistema asigna el **estudio** al **bioinformático** y lo pasa a **En análisis por un bioinformático**.
5. El sistema quita el **estudio** de la lista de los demás **bioinformáticos**.

**Excepciones:**
- Si otro **bioinformático** lo tomó antes, el sistema lo informa, mantiene la asignación existente y actualiza la lista.

---

## 36. Registrar variantes y finalizar el análisis

**Objetivo:** Que el bioinformático registre las variantes encontradas y finalice el análisis, de modo que el resultado quede informado al médico tratante y al paciente.

**Contexto:**
- El **estudio** está **En análisis por un bioinformático** y asignado al **bioinformático**.
- Restricción: el análisis de los **datos crudos** se hace fuera del sistema. En el sistema solo se registran las **variantes genéticas**.
- Restricción: la **clasificación de variante** la informa la **Bioinformática API** y el **bioinformático** no puede editarla.
- Pendiente (P5): cómo se informa una variante VUS en el **resultado del estudio**.

**Actores:** Bioinformático, Sistema.

**Recursos:** Lista de genes, selector de variantes de la Bioinformática API, plantilla del resultado.

**Episodios:**
1. El **bioinformático** indica el **gen** de la **lista de genes** en el que halló una variante.
2. El sistema consulta la **Bioinformática API** y presenta las **variantes genéticas** conocidas de ese **gen**.
3. El **bioinformático** registra la **variante genética** encontrada, y el sistema muestra su **clasificación de variante**. Los episodios 1 a 3 se repiten por cada **gen** con hallazgos.
4. El **bioinformático** finaliza el análisis, haya registrado o no **variantes genéticas**.
5. El sistema informa el resultado: genera el **resultado del estudio** en PDF, pasa el **estudio** a **Resultado disponible** y envía un **aviso** por mail al **médico tratante** y al **paciente**.

**Excepciones:**
- Si no se registró ninguna **variante genética**, el **resultado del estudio** es negativo.
- Si el **ADN** resulta insuficiente, se continúa con SOLICITAR EL REMUESTREO (25).

---

## 37. Consultar el resultado del estudio

**Objetivo:** Que el médico tratante conozca el resultado del estudio que solicitó.

**Contexto:**
- El **estudio** está en **Resultado disponible**. La generación y el aviso se describen en el escenario 36.
- Desde aquí, el **médico tratante** puede iniciar SOLICITAR EL REANÁLISIS DE UN ESTUDIO (39) si persiste una sospecha no evaluada.

**Actores:** Médico tratante.

**Recursos:** PDF del resultado del estudio.

**Episodios:**
1. El **médico tratante** abre el **estudio** desde su listado.
2. El **médico tratante** revisa si el resultado es positivo o negativo y cuáles son las **variantes genéticas** con su **clasificación de variante**.
3. El **médico tratante** descarga el PDF del **resultado del estudio**.

**Excepciones:** Ninguna identificada.

---

## 38. Descargar el resultado del estudio

**Objetivo:** Que el paciente obtenga su resultado desde la plataforma.

**Contexto:**
- El **estudio** está en **Resultado disponible**. La generación y el aviso se describen en el escenario 36.
- Restricción: por mail solo llega el **aviso**. El PDF se descarga desde la plataforma.
- Restricción: si el **paciente** es menor de edad, accede el padre o la madre con las **credenciales de acceso** asociadas a su mail.

**Actores:** Paciente.

**Recursos:** PDF del resultado del estudio.

**Episodios:**
1. El **paciente** abre su **estudio** desde la lista de sus **estudios**.
2. El **paciente** solicita la descarga del **resultado del estudio**.
3. El sistema entrega el PDF del **resultado del estudio**.

**Excepciones:** Ninguna identificada.

---

## 39. Solicitar el reanálisis de un estudio

**Objetivo:** Que el médico tratante solicite analizar otros genes de un estudio ya informado, sin una nueva extracción.

**Contexto:**
- El **estudio** está en **Resultado disponible** y el **médico tratante** tiene una nueva sospecha.
- Restricción: se reutilizan los **datos crudos**. No se toma una nueva **muestra de sangre** ni se vuelve a leer el **ADN**.
- Pendiente (P6): el costo adicional y la secuencia de estados del reanálisis.

**Actores:** Médico tratante, Sistema.

**Recursos:** Estudio previo, datos crudos guardados, Bioinformática API.

**Episodios:**
1. El **médico tratante** abre el **estudio** informado y solicita su reanálisis.
2. El **médico tratante** indica la nueva **patología lisosomal** sospechada.
3. El sistema consulta la **Bioinformática API** y presenta los **genes** que todavía no se analizaron.
4. El **médico tratante** solicita el reanálisis de esos **genes**.
5. El sistema registra la solicitud sobre el mismo **estudio**, con los mismos **datos crudos**.

**Excepciones:**
- Si todos los **genes** de la nueva patología ya se analizaron, el sistema lo informa y no registra la solicitud.

---

# H. Comunicación

## 40. Consultar al chatbot

**Objetivo:** Que el paciente consulte dudas sobre las patologías lisosomales desde la plataforma.

**Contexto:**
- El **paciente** ingresó al sistema.
- Restricción: el **chatbot** es un servicio externo, responde sobre las **patologías lisosomales** y no deriva a una persona.
- Pendiente (P10): el canal de acceso (plataforma o WhatsApp).

**Actores:** Paciente, Chatbot (servicio externo).

**Recursos:** Ventana de chat, chatbot.

**Episodios:**
1. El **paciente** abre el **chatbot** por el canal habilitado.
2. El **paciente** escribe su consulta sobre una **patología lisosomal**.
3. El sistema envía la consulta al **chatbot**.
4. El **chatbot** devuelve una respuesta.
5. El sistema presenta la respuesta al **paciente**.

**Excepciones:**
- Si el **chatbot** no responde, el sistema informa que no está disponible [supuesto].

---

## 41. Consultar avisos pendientes

**Objetivo:** Que cualquier rol vea en la plataforma lo que tiene pendiente.

**Contexto:**
- El usuario ingresó al sistema y los **avisos** que ve dependen de su rol. Se ejemplifica con el **paciente**.
- Restricción: al **paciente** se le comunica por mail y dentro del sistema, nunca al celular.
- Pendiente (P16): la entrevista no define cómo se organizan, leen o eliminan los **avisos**.

**Actores:** Paciente (o cualquier rol).

**Recursos:** Lista de avisos.

**Episodios:**
1. El sistema indica que hay **avisos** pendientes.
2. El **paciente** abre la lista de **avisos**.
3. El **paciente** abre un **aviso**.
4. El sistema presenta la pantalla del **estudio** relacionada con ese **aviso**.

**Excepciones:**
- Si no hay **avisos** pendientes, la lista se muestra vacía.

---

# Cambios respecto de la v2

## Criterios generales aplicados

- Los títulos pasaron a verbo en infinitivo y, cuando fue posible, coinciden con un verbo del LEL corregido.
- Se redujeron los verbos genéricos (seleccionar, confirmar, ingresar, validar) y se reemplazaron por verbos del dominio.
- Ningún escenario supera los 5 episodios, y se evitó mezclar dos actores en un mismo episodio.
- Las excepciones son solo obstáculos. Se eliminaron las que describían un abandono voluntario ("no confirma") y los textos de relleno del tipo "No se identificaron excepciones específicas confirmadas".
- Los actores listados son los que efectivamente actúan en algún episodio.
- Se evitaron los ciclos entre escenarios (13 y 14, 28 y 30).
- Los pendientes se numeraron todos (P1 a P17).
- Se mantuvieron las marcas [deseo] y [supuesto].

## Cambios por escenario

| v3 | Cambio | Origen |
|---|---|---|
| 1 | Se aclara qué roles usan autoalta (el transportista y el gerente médico dependen del administrador general). Se agrega P11. | Revisión |
| 2 | Pasa a ser el único camino de alta del transportista y del gerente médico si se adopta la autoalta. Un transportista por provincia. | Revisión |
| 3 | Se renombra y se unifica con el LEL ("Activar la cuenta"). | Revisión |
| 4 | Deja de ser solo la verificación adicional y pasa a ser el ingreso al sistema (verbo V2 del LEL): camino principal, reintento con credenciales incorrectas y bloqueo por intentos. | Revisión + LEL |
| 5, 6 | Se aclara que la relación con los genes la mantiene la Bioinformática API. Se agrega P13. | Revisión |
| 7 | Se corrige el último episodio para el caso del síntoma cardinal. | Revisión |
| 8 | Se agrega el episodio del paciente informando sobre su familia y la excepción del módulo caído. | Revisión |
| 9 | Se agrega la regla de correspondencia al contexto, diagnósticos presuntivos múltiples y el episodio de confirmación del alta. Pasa de 6 a 5 episodios. | Revisión |
| 10 | Se corrige la contradicción de contexto y excepción, y se alinea con el LEL (patologías sospechadas en plural). Pompe urgente se asigna si entre las patologías está Pompe. Se agrega P15. | Revisión + LEL |
| 11, 12 | Se reemplazan las excepciones que no eran obstáculos. Se agrega P14. | Revisión |
| 13, 14 | Se elimina el ciclo entre ambos. El uso del cupón se informa en el pago (13) y no en el subescenario. | Revisión |
| 15 a 17 | Ajustes de verbos y restricciones. | Revisión |
| 18 | Se agrega la gestión telefónica con la obra social como episodio, la bandeja incluye los rechazados con demanda. | Revisión + LEL |
| 19 | Se aclara que el estudio sigue Rechazado hasta que se registre la nueva respuesta (coincide con el verbo V14 del LEL). | Revisión + LEL |
| 20 | Texto del grupo (23 de su numeración), con la publicación de la orden y del consentimiento separada de la reserva. | Grupo + revisión |
| 21 | Texto del grupo (24). Pasa a ser un escenario principal y no un subescenario del 20. | Grupo + revisión |
| 22 | Texto del grupo (25) con el estado al que vuelve el estudio explicitado y la excepción del turno vencido. | Grupo + revisión |
| 23 | Se mantiene el texto de la v2: registro de la inasistencia, aviso y nueva reserva. | v2 |
| 24 | Texto del grupo (27): el volumen viaja en la notificación y el sistema decide si pasa a Listo para retirar. | Grupo |
| 25 | Mezcla del texto del grupo (28), la v2 y el LEL (E11 y V21): lo invocan el sistema y el bioinformático. | Grupo + v2 + LEL |
| 26 | Texto del grupo (29) con la generación de la orden del día de la v2, y marca [deseo]. | Grupo + v2 |
| 27 | Texto del grupo (30) con un cuarto episodio más claro. | Grupo |
| 28 | Texto del grupo (31). | Grupo |
| 29 | Texto del grupo (33), con el sistema como actor. | Grupo |
| 30 | Texto de la v2, con el contexto del grupo (34). | v2 + grupo |
| 31 | Texto del grupo (35). | Grupo |
| 32 | Texto de la v2, con el contexto del grupo (36). | v2 + grupo |
| 33 | Texto del grupo (32), con la marca [deseo] y P9. | Grupo + v2 |
| 34 | Texto del grupo (37), con la excepción del archivo vacío. | Grupo + v2 |
| 35 | Texto del grupo (38). | Grupo |
| 36 | Mezcla de la v2 y del grupo (39), reducida de 6 a 5 episodios. | v2 + grupo |
| 37, 38 | Se mantiene la separación de la v2 (médico y paciente), con el contenido del resultado en 37. | v2 + grupo |
| 39 | Texto de la v2, con el contexto del grupo (42). | v2 + grupo |
| 40 | Texto del grupo (43). | Grupo |
| 41 | Texto de la v2, con el contexto del grupo (44). | v2 + grupo |

## Correspondencia con la numeración del grupo

El grupo trabajó los escenarios 23 a 44 con la numeración de la v1. En esta versión se usa el orden de la v2.

| Grupo | v3 | Grupo | v3 | Grupo | v3 |
|---|---|---|---|---|---|
| 23 | 20 | 31 | 28 | 39 | 36 |
| 24 | 21 | 32 | 33 | 40 | 37 y 38 |
| 25 | 22 | 33 | 29 | 41 | 38 |
| 26 | 23 | 34 | 30 | 42 | 39 |
| 27 | 24 | 35 | 31 | 43 | 40 |
| 28 | 25 | 36 | 32 | 44 | 41 |
| 29 | 26 | 37 | 34 | | |
| 30 | 27 | 38 | 35 | | |

---

# Pendientes y decisiones

| ID | Tema | Escenarios |
|---|---|---|
| D1 | Mecanismo de alta de usuarios: autoalta o administrador general. | 1, 2 |
| P1 | Si la regla de correspondencia clínica se aplica a una sospecha familiar sin síntomas. | 9 |
| P2 | Consecuencia de superar las cinco inasistencias. | 23 |
| P3 | Quién y cómo registra la inasistencia. | 23 |
| P4 | Estado del estudio al cancelar un turno. Se asume que vuelve a Pagado o Autorizado. | 22 |
| P5 | Cómo se informa una variante de significado incierto (VUS) en el resultado. | 36 |
| P6 | Costo adicional y secuencia de estados del reanálisis. | 39 |
| P7 | Cómo llega el volumen de la muestra al sistema y quién detecta que el ADN es insuficiente. | 24, 25 |
| P8 | Si tras un rechazo el paciente puede optar por el pago particular. | 18 |
| P9 | Integración de geolocalización del transportista. | 33 |
| P10 | Canal de acceso al chatbot (plataforma o WhatsApp). | 40 |
| P11 | Si el alta por autoalta de un administrativo o de un bioinformático requiere aprobación. | 1 |
| P12 | Criterio para reconocer un dispositivo o una red nuevos, y cómo se restablece una cuenta bloqueada. | 4 |
| P13 | Efecto de modificar los síntomas de una patología sobre los pacientes ya registrados. | 6 |
| P14 | Liquidación de la diferencia cuando la obra social cubre solo un porcentaje. | 12, 18 |
| P15 | Si los genes de los hallazgos secundarios cuentan para la tarifa. | 10 |
| P16 | Cómo se organizan, leen y eliminan los avisos. | 41 |
| P17 | Contratación del módulo de optimización de recorridos. | 26 |
