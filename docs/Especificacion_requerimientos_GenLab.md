# Especificación de requerimientos: plataforma del laboratorio de genética y módulo Chatbot (módulo adicional 8)

> Documento de alcance funcional de lo que construye nuestro grupo. Sigue el formato de la especificación de requerimientos de ejemplo (descripción, requerimientos funcionales, notas y permisos por módulo). Se apoya en los 41 escenarios de Leite (v3), el glosario LEL y el PDF "Módulos adicionales" de la cátedra.

## Nota de procedencia (leer antes de usar este documento)

- Las reglas de negocio salen de la entrevista al Product Owner y de los escenarios v3. Los identificadores P1 a P17 y D1 son los pendientes de ese documento.
- Lo que viene del PDF "Módulos adicionales" y no estaba en los escenarios se marca **[PDF]**.
- Lo que no surge de ninguna fuente y decidimos para poder avanzar se marca **[supuesto]**. Lo que el PO pidió sujeto a costo o factibilidad se marca **[deseo]**.
- El PDF de módulos adicionales es muy breve en varios módulos (el chatbot tiene una sola línea). Todo lo que se agrega al detalle del chatbot es **[supuesto]** y está listado en las decisiones pendientes.
- Los puntos de integración (qué datos manda y recibe cada módulo de otro grupo) todavía no tienen contrato cerrado. Se definen con cada grupo (ver decisiones pendientes).

## Contexto

Un laboratorio de genética realiza estudios de exoma clínico para pacientes con sospecha de patologías lisosomales (enfermedad de Fabry, enfermedad de Pompe, mucopolisacaridosis tipo 1, enfermedad de Gaucher y ASMD). El **médico tratante** solicita el estudio, el **paciente** lo paga o lo cubre su **obra social**, se toma la **muestra de sangre** en un **laboratorio de extracción**, un **transportista** la lleva al **laboratorio central**, los estudios se agrupan en **lotes** de 10 que viajan a **Corea** por FedEx con permiso del Ministerio de Salud, y al volver los **datos crudos** un **bioinformático** registra las variantes y se informa el resultado.

La aplicación completa se compone de módulos que desarrollan distintos grupos y que se consumen entre sí. A nosotros nos tocó el **módulo 8, Chatbot para el paciente**, que además de usarse en nuestra plataforma lo van a consumir otros grupos. Por eso este documento cubre dos cosas: la plataforma del laboratorio, que consume los módulos de los demás, y el chatbot, que es el módulo que ofrecemos.

## Alcance: qué construimos y qué consumimos

| Módulo adicional (PDF) | Quién lo construye | Qué hacemos nosotros |
|---|---|---|
| 1. Familiograma | Otro grupo | Cargar familiares y consumir el servicio que devuelve el PDF (escenario 8) |
| 2. Términos médicos estandarizados (SNOMED) | Otro grupo | Buscador de síntomas que consume el servicio, sin texto libre (escenario 7) |
| 3. Sistema de vouchers (cupones) | Otro grupo | Consumir obtener, validar y marcar como usado. La gestión y asignación de cupones es nuestra |
| 4. CDSS, sistema de soporte | Otro grupo | Consumir "síntomas a patología" al dar de alta al paciente y permitir elegir la estrategia |
| 5. Apigen | Otro grupo | Consumir genes por patología, hallazgos secundarios, variantes y confirmación de diagnóstico |
| 6. Obras sociales | Otro grupo | Consumir la lista con porcentaje de cobertura y el alta de estudio para autorización |
| 7. Módulo de avisos | Otro grupo | Consumir el envío por mail (o WhatsApp o Telegram). La lista de avisos en la plataforma es nuestra |
| **8. Chatbot para el paciente** | **Nuestro grupo** | **Construirlo como servicio y usarlo en nuestra plataforma** |
| 9. Optimización de recorrido | Otro grupo | Consumir "direcciones a recorrido ordenado" para la orden del día |
| 10. FedEx | Otro grupo | Consumir la programación del retiro y la consulta de estado |

Queda a nuestro cargo, aunque no esté en el PDF: la API simulada del Ministerio de Salud, el simulador del laboratorio de extracción (Telegram) y el pago simulado.

## Actores/roles

- **Administrador general**: da de alta usuarios de cualquier rol, excepto pacientes.
- **Gerente médico**: configura patologías y síntomas, genera y asigna cupones.
- **Médico tratante**: registra pacientes, solicita estudios, consulta resultados, entrega cupones.
- **Paciente** (o su padre o madre si es menor): paga, saca turno, descarga documentos y resultado, consulta al chatbot.
- **Administrativo del laboratorio**: emite presupuestos, registra autorizaciones, gestiona lotes y retiros, carga datos crudos.
- **Transportista**: recorre las paradas de su orden del día y entrega las muestras.
- **Bioinformático**: toma estudios y registra variantes.
- **Actores externos**: laboratorio de extracción, obra social, Ministerio de Salud, FedEx, módulos de otros grupos.

## Componentes de la aplicación

Propuesta (no es la decisión final):

- **Aplicación web** responsive, usable desde computadora y celular. Un mismo frontend con una vista por rol.
- **Backend y base de datos** propios para el estudio, los lotes, los turnos, los avisos y el registro financiero.
- **Adaptadores de integración**: una capa por cada módulo externo, para poder cambiar el contrato o usar un simulador sin tocar el resto.
- **Simuladores** para quienes no operan en la plataforma: laboratorio de extracción, Ministerio de Salud y pago.
- **Servicio de Chatbot** independiente, con su propia API y despliegue, consumible por otros grupos.

## Resumen de decisiones pendientes

| # | Decisión | Depende de | Bloquea |
|---|---|---|---|
| 1 | Contrato de cada módulo externo (campos, formato, autenticación, errores) | Acuerdo con cada grupo | Adaptadores de integración |
| 2 | Obras sociales (MA6) ofrece una web de autorización propia, pero el escenario 18 asume que el administrativo gestiona la respuesta por teléfono. ¿Qué rige? | Cátedra | M4, registro de la autorización |
| 3 | FedEx (MA10) devuelve una URL para consultar el estado, pero el escenario 32 asume que FedEx llama a la URL del lote. ¿Consultamos nosotros o nos llaman? | Cátedra y grupo de FedEx | M7, registro del retiro |
| 4 | Estrategia del CDSS: el PDF dice que cada grupo la elige y puede cambiarla. ¿Quién la cambia (gerente médico) y con qué valores por defecto? | Equipo | M2 y alta de paciente |
| 5 | Canal del chatbot: plataforma o WhatsApp (P10) | Cátedra | Chatbot |
| 6 | Tecnología del chatbot (modelo de lenguaje, costo, proveedor) y fuente de la base de conocimiento | Equipo | Chatbot |
| 7 | Cómo autentica el chatbot a los grupos consumidores (clave de API, sin autenticación) | Equipo y consumidores | Chatbot |
| 8 | Qué responde el chatbot ante consultas sobre síntomas o resultados personales | Cátedra | Chatbot, control de alcance |
| 9 | Pendientes de negocio P1 a P17 y D1 de los escenarios | PO | Según cada escenario |

## Requerimientos por módulo

Los módulos propios se numeran M1 a M10. Los módulos de la cátedra se nombran "MA" (por ejemplo MA8 es el chatbot).

---

### M1. Acceso y usuarios

#### Descripción

Registro, alta, activación e ingreso de todos los roles. Los datos genéticos son críticos para el PO, así que el ingreso tiene una verificación adicional.

#### Requerimientos funcionales

- M1-RF1. El sistema deberá permitir la autoalta de un médico tratante, un administrativo del laboratorio o un bioinformático, con nombre, apellido, teléfono, mail y contraseña (escenario 1, decisión D1).
- M1-RF2. Para el médico tratante, el alta deberá pedir además la matrícula y las especialidades elegidas de un catálogo estandarizado. La matrícula no se valida contra un servicio externo.
- M1-RF3. El sistema deberá rechazar un registro con mail ya existente o con datos obligatorios faltantes.
- M1-RF4. El administrador general deberá poder dar de alta usuarios de cualquier rol, excepto paciente, y el sistema deberá enviar las credenciales por mail (escenario 2).
- M1-RF5. El sistema deberá permitir un solo transportista por provincia y rechazar el alta de un segundo **[supuesto]**.
- M1-RF6. El gerente médico y el transportista solo podrán ser dados de alta por el administrador general **[supuesto]**.
- M1-RF7. El paciente deberá cambiar la contraseña inicial en su primer ingreso, antes de ver cualquier otra pantalla. Si es menor de edad, lo hace su padre o madre (escenario 3).
- M1-RF8. El ingreso deberá pedir un código de verificación enviado por mail cuando el dispositivo o la red sean nuevos **[deseo]** (escenario 4).
- M1-RF9. El sistema deberá bloquear la cuenta tras 5 intentos fallidos consecutivos **[supuesto]**.
- M1-RF10. El código de verificación deberá vencer a los 10 minutos y permitir solicitar uno nuevo **[supuesto]**.

#### Notas

- Pendientes: P11 (aprobación del alta de administrativos y bioinformáticos) y P12 (criterio de dispositivo nuevo y desbloqueo de cuentas).
- El pedido de la cátedra de proteger los datos genéticos aplica a todo el sistema: sesiones con vencimiento y contraseñas almacenadas con hash.

#### Permisos

- Autoalta: pública para los tres roles indicados. Alta por administrador: solo administrador general.

---

### M2. Configuración médica

#### Descripción

El gerente médico mantiene el catálogo de patologías lisosomales y los síntomas que las caracterizan.

#### Requerimientos funcionales

- M2-RF1. El sistema deberá permitir dar de alta una patología lisosomal con un síntoma cardinal y síntomas secundarios (escenario 5).
- M2-RF2. Los síntomas se cargarán con el buscador de SNOMED (M3-RF1), sin texto libre.
- M2-RF3. El sistema deberá impedir duplicar una patología existente.
- M2-RF4. El sistema deberá permitir modificar el síntoma cardinal y los síntomas secundarios de una patología. El cambio rige para los próximos pacientes **[supuesto]** (escenario 6).
- M2-RF5. El sistema deberá permitir elegir la estrategia del CDSS entre las tres del PDF: patología con más síntomas coincidentes, patología con más síntomas cardinales coincidentes, o menor diferencia entre los síntomas de la patología y los del paciente **[PDF]**.
- M2-RF6. Los genes de cada patología no se cargan acá: los mantiene Apigen.

#### Notas

- Pendiente P13 (efecto de modificar síntomas sobre pacientes ya registrados) y la decisión 4 de la tabla anterior.

#### Permisos

- Accesible solo para el gerente médico.

---

### M3. Consulta médica: pacientes y estudios

#### Descripción

El médico tratante registra al paciente durante la consulta y solicita el estudio con su lista de genes.

#### Requerimientos funcionales

- M3-RF1. El sistema deberá ofrecer un buscador de síntomas que consulte el servicio de SNOMED desde 3 letras, presente las coincidencias y no admita texto libre (escenario 7, **[PDF]** MA2).
- M3-RF2. El sistema deberá permitir cargar el alta del paciente con DNI, nombre, apellido, fecha de nacimiento, teléfono y mail. Si es menor, el mail es el de sus padres (escenario 9).
- M3-RF3. El sistema deberá permitir indicar uno o más diagnósticos presuntivos y el tipo de sospecha (clínica o familiar), y cargar el resumen de historia clínica y los síntomas.
- M3-RF4. El dictado por voz del resumen de historia clínica queda como **[deseo]**. Si no está disponible, se escribe.
- M3-RF5. Todos los datos del alta serán obligatorios, salvo el familiograma.
- M3-RF6. En una sospecha clínica, el sistema deberá verificar la regla de correspondencia clínica (síntoma cardinal o dos síntomas secundarios) consultando al CDSS (MA4), bloquear el alta si no se cumple e indicar qué falta.
- M3-RF7. Si el DNI ya existe, el sistema deberá mostrar al paciente existente y continuar con el alta del estudio.
- M3-RF8. Al dar de alta al paciente, el sistema deberá enviarle sus credenciales por mail.
- M3-RF9. El sistema deberá permitir cargar familiares (parentesco, nombre, diagnóstico y síntomas) y obtener el familiograma en PDF del módulo MA1. Si el módulo falla, el alta continúa con el familiograma vacío **[supuesto]** (escenario 8).
- M3-RF10. El sistema deberá permitir solicitar un estudio para un paciente con una o más patologías sospechadas y obtener la lista de genes de Apigen (MA5), incluidos los hallazgos secundarios si se piden (escenario 10).
- M3-RF11. El médico podrá agregar genes manualmente.
- M3-RF12. El estudio quedará en estado Creado. Si entre las patologías está Pompe y el paciente tiene menos de 4 meses, el estudio tendrá la prioridad Pompe urgente.
- M3-RF13. Si Apigen no responde, el sistema no permitirá solicitar el estudio **[supuesto]**.

#### Notas

- Pendientes P1 (regla de correspondencia en sospecha familiar) y P15 (los hallazgos secundarios y la tarifa).

#### Permisos

- Accesible solo para el médico tratante. El gerente médico usa el buscador de síntomas en M2.

---

### M4. Presupuesto, cobertura y pago

#### Descripción

Desde el estudio Creado hasta que queda habilitado para sacar turno, ya sea Pagado o Autorizado.

#### Requerimientos funcionales

- M4-RF1. El administrativo deberá ver una bandeja de estudios Creados sin presupuesto y emitir el presupuesto. El importe es fijo: USD 500 hasta 5 genes y USD 30 por cada gen adicional, con la extracción y el turno incluidos (escenario 11).
- M4-RF2. Al emitirse el presupuesto, el paciente deberá recibir un aviso **[supuesto]**.
- M4-RF3. El paciente deberá poder elegir la cobertura por obra social, ver la lista con el porcentaje de cobertura (MA6) y dejar el estudio a la espera de la autorización (escenario 12).
- M4-RF4. Si la obra social no figura en la lista, solo queda el pago particular **[supuesto]**.
- M4-RF5. El paciente deberá poder pagar de forma particular con un pago simulado que se asienta en el registro financiero (escenario 13). A futuro se integraría Mercado Pago.
- M4-RF6. El paciente deberá poder aplicar un cupón de descuento adjuntando el PDF o su código. El sistema deberá consultar al módulo de cupones (MA3) si está Vigente y mostrar el nuevo importe. Al pagar, informará el uso del cupón (escenario 14).
- M4-RF7. El administrativo deberá registrar la respuesta de la obra social como Autorizado o Rechazado, con el motivo en el segundo caso, y el sistema deberá asentar la operación y avisar al paciente (escenario 18). Ver la decisión 2 de la tabla.
- M4-RF8. El paciente con un estudio Rechazado deberá ver el motivo y poder adjuntar el PDF de la demanda para pedir la reautorización. El sistema rechazará archivos que no sean PDF (escenario 19).
- M4-RF9. Un estudio Autorizado se considera autorizado y pagado.

#### Notas

- Pendientes P8 (pago particular tras un rechazo) y P14 (diferencia a cargo del paciente si la cobertura es parcial).

#### Permisos

- Presupuesto y autorizaciones: administrativo. Cobertura, pago y demanda: paciente.

---

### M5. Cupones de descuento

#### Descripción

El gerente médico genera cupones y los reparte entre médicos, que a su vez los asignan a pacientes. La creación, la vigencia y el uso los resuelve el módulo MA3.

#### Requerimientos funcionales

- M5-RF1. El gerente médico deberá poder definir el descuento y la cantidad, y el sistema deberá pedirlos al módulo de cupones y mostrarlos Vigentes con su PDF y QR (escenario 15).
- M5-RF2. El gerente médico deberá poder asignar uno o más cupones Vigentes a un médico tratante buscado por nombre o matrícula, y el médico recibirá un aviso (escenario 16).
- M5-RF3. El médico tratante deberá poder asignar un cupón disponible a un paciente. El sistema lo descontará de los disponibles y lo publicará en la vista del paciente (escenario 17).
- M5-RF4. Si el médico no tiene cupones, la asignación se deshabilita.
- M5-RF5. Si el módulo de cupones rechaza la solicitud, el sistema informa el error y no muestra cupones nuevos.

#### Permisos

- Generar y asignar a médicos: gerente médico. Asignar a pacientes: médico tratante.

---

### M6. Turno y extracción

#### Descripción

Reserva del turno en el laboratorio de extracción, documentos para asistir, cancelaciones, inasistencias, notificación de la muestra y remuestreo.

#### Requerimientos funcionales

- M6-RF1. El sistema deberá mostrar en un mapa los laboratorios de extracción (hay 100 en el país) y permitir elegir uno y un turno libre (escenario 20).
- M6-RF2. Los turnos duran 15 minutos, para una persona, de lunes a viernes de 9 a 18, sin feriados. El sistema los genera con esa regla **[supuesto]**.
- M6-RF3. Solo podrá sacar turno un estudio Pagado o Autorizado, o uno con una nueva reserva habilitada por cancelación, inasistencia o remuestreo.
- M6-RF4. Al reservar, el estudio pasará a Turno sacado, se programará un recordatorio por mail y se publicarán la orden de extracción y el consentimiento informado.
- M6-RF5. Si el turno se ocupa antes de reservarlo, el sistema deberá mostrar los turnos libres actualizados.
- M6-RF6. El paciente deberá poder descargar la orden de extracción (fecha, hora, laboratorio e indicaciones) y el consentimiento informado para imprimir. El firmado se entrega en papel y no se sube al sistema (escenario 21).
- M6-RF7. El paciente deberá poder cancelar un turno futuro sin costo, y el estudio vuelve al estado previo **[supuesto]**. Un turno cuya hora ya pasó no se cancela (escenario 22).
- M6-RF8. El sistema deberá registrar una inasistencia, avisar la cantidad acumulada y permitir reprogramar. Al llegar a 5 avisa pero no aplica bloqueo hasta resolver P2 (escenario 23).
- M6-RF9. El sistema deberá recibir, sin intervención de personas, la notificación del laboratorio de extracción con el estudio y el volumen de la muestra, y pasar el estudio a Listo para retirar si hay al menos 2 ml (escenario 24).
- M6-RF10. Con menos de 2 ml, o con ADN insuficiente informado por el bioinformático, el sistema deberá habilitar un remuestreo sin costo y sin crear un estudio nuevo, y avisar al médico y al paciente (escenario 25).

#### Notas

- La notificación por Telegram con un bot es un **[deseo]** del PO. Mientras tanto se usa un endpoint con un simulador.
- Pendientes P2, P3, P4 y P7.

#### Permisos

- Turnos y documentos: paciente. Notificación: actor externo. Remuestreo por ADN: bioinformático.

---

### M7. Logística y envío a Corea

#### Descripción

Desde la muestra lista para retirar hasta que el lote sale en FedEx con el permiso del Ministerio de Salud.

#### Requerimientos funcionales

- M7-RF1. Cada día hábil, el sistema deberá enviar al módulo de optimización (MA9) las direcciones de los laboratorios con muestras por retirar en la provincia y presentar al transportista su orden del día numerada, con las muestras por parada (escenario 26).
- M7-RF2. En fines de semana y feriados no se genera orden del día. Si no hay muestras, el sistema lo informa.
- M7-RF3. El recorrido es fijo: el transportista no puede reordenar ni saltear paradas.
- M7-RF4. El transportista deberá registrar el retiro de cada parada y el sistema pasará esas muestras a En camino al laboratorio central (escenario 27).
- M7-RF5. El transportista deberá registrar su llegada al laboratorio central. El sistema pasará los estudios a En laboratorio central y los incorporará al lote abierto por orden de llegada (escenario 28).
- M7-RF6. El lote se cierra solo al llegar a 10 estudios. Un lote incompleto queda abierto, aunque termine el día.
- M7-RF7. Si entra un estudio Pompe urgente, el sistema cerrará el lote con los estudios que tenga y abrirá otro (escenario 30). Es la única excepción a los 10 estudios.
- M7-RF8. Al cerrar un lote, el sistema deberá generar el CSV de pacientes, enviarlo a la API del Ministerio de Salud, recibir el permiso en PDF y asociarlo a cada estudio. Sin permiso, no se puede programar el retiro (escenario 29).
- M7-RF9. El administrativo deberá poder programar el retiro de un lote autorizado, eligiendo día y hora de 9 a 18 en días hábiles sin feriados, y el sistema lo enviará a FedEx (MA10) con la URL del lote (escenario 31).
- M7-RF10. Cuando FedEx retire el paquete, el sistema pasará el lote y sus estudios a En viaje a Corea y sellará el lote (escenario 32). Ver la decisión 3 de la tabla.
- M7-RF11. Si FedEx no confirma la programación o la señal de retiro no llega, el lote mantiene su estado.
- M7-RF12. El administrativo deberá poder consultar la ubicación de una muestra en traslado en un mapa **[deseo]** (escenario 33, P9).

#### Notas

- La app del transportista es un **[deseo]** del PO. Se implementa como una vista web responsive.
- Pendientes P9 y P17.

#### Permisos

- Orden del día y retiros: transportista. Lotes y FedEx: administrativo.

---

### M8. Bioinformática y resultados

#### Descripción

El administrativo carga los datos crudos que vuelven de Corea, el bioinformático registra las variantes y el sistema informa el resultado.

#### Requerimientos funcionales

- M8-RF1. El administrativo deberá poder adjuntar los datos crudos a cada estudio En viaje a Corea. El sistema los asocia, pasa el estudio a En el área de bioinformática y avisa por mail a todos los bioinformáticos (escenario 34). Rechaza archivos vacíos **[supuesto]**.
- M8-RF2. El bioinformático deberá ver la lista de estudios disponibles, con los Pompe urgente primero y el resto por orden de llegada (escenario 35).
- M8-RF3. Al tomar un estudio, el sistema lo asigna, lo pasa a En análisis por un bioinformático y lo quita de la lista de los demás. Si otro lo tomó antes, lo informa.
- M8-RF4. Por cada gen con hallazgos, el bioinformático deberá elegir la variante de las que devuelve Apigen. La clasificación (patogénica, benigna o VUS) la informa Apigen y no se edita (escenario 36).
- M8-RF5. Al finalizar el análisis, con o sin variantes, el sistema deberá generar el PDF del resultado, pasar el estudio a Resultado disponible y avisar por mail al médico y al paciente. Sin variantes, el resultado es negativo.
- M8-RF6. El médico deberá poder ver el resultado, las variantes con su clasificación y descargar el PDF (escenario 37).
- M8-RF7. El paciente deberá descargar el PDF desde la plataforma. El resultado no se envía por mail (escenario 38).
- M8-RF8. El médico deberá poder solicitar un reanálisis con una nueva patología sospechada, sin nueva extracción, con los genes todavía no analizados (escenario 39).

#### Notas

- Pendientes P5 (cómo se informa una VUS) y P6 (costo y estados del reanálisis).

#### Permisos

- Datos crudos: administrativo. Análisis: bioinformático. Resultado: médico tratante y paciente.

---

### M9. Avisos

#### Descripción

Cada rol ve en la plataforma lo que tiene pendiente. El envío por mail lo hace el módulo MA7.

#### Requerimientos funcionales

- M9-RF1. El sistema deberá indicar que hay avisos pendientes y mostrar una lista según el rol (escenario 41).
- M9-RF2. Abrir un aviso deberá llevar a la pantalla del estudio relacionado.
- M9-RF3. Los avisos al paciente se envían por mail y se muestran en la plataforma, nunca al celular.
- M9-RF4. Si no hay avisos, la lista se muestra vacía.

#### Notas

- Pendiente P16 (cómo se organizan, leen y eliminan los avisos).

#### Permisos

- Cada usuario ve solo sus avisos.

---

### M10. Integraciones con módulos externos

#### Descripción

Capa de adaptadores entre nuestra plataforma y los módulos de otros grupos, con simuladores para poder desarrollar y demostrar sin depender de ellos.

#### Requerimientos funcionales

- M10-RF1. Cada módulo externo deberá consumirse a través de un adaptador con una interfaz propia, de modo que el contrato pueda cambiar sin modificar el resto del sistema.
- M10-RF2. Cada adaptador deberá tener un simulador local con datos de ejemplo, activable por configuración.
- M10-RF3. Ante la caída de un módulo externo, el sistema deberá informar el error al usuario y no perder el trabajo ya cargado.
- M10-RF4. El sistema deberá incluir un panel que simule a los actores sin acceso a la plataforma: laboratorio de extracción, Ministerio de Salud y FedEx.

Contratos mínimos que necesitamos de cada módulo **[PDF]**:

| Módulo | Entrada | Salida |
|---|---|---|
| MA1 Familiograma | Parentescos y datos de familiares | PDF del familiograma |
| MA2 SNOMED | Texto (3 letras o más), con paginación | Términos que coinciden |
| MA3 Cupones | Obtener, validar (fecha y no uso), marcar como usado | Cupón con estado |
| MA4 CDSS | Lista de síntomas y estrategia | Patología, o "no compatible con patologías lisosomales" |
| MA5 Apigen | Patología, gen, lista de variantes | Genes, hallazgos secundarios, variantes, confirmación de diagnóstico |
| MA6 Obras sociales | Alta de estudio (nombre y fecha) | Lista de obras sociales con cobertura, estado de autorización |
| MA7 Avisos | Destinatario, canal y mensaje | Confirmación de envío |
| MA9 Optimización | Direcciones de un transportista | Recorrido ordenado |
| MA10 FedEx | Día, hora y lugar del retiro | URL de consulta de estado |

---

### M11. Chatbot para el paciente (módulo adicional 8)

#### Descripción

Servicio conversacional especializado en estudios genéticos, que el paciente consulta para resolver dudas. Se publica como un servicio independiente con una API que consumen otros grupos y que usamos en nuestra propia plataforma (escenario 40). La cátedra lo define con una sola línea ("Especializado en estudios genéticos"), así que el detalle de abajo es nuestra propuesta de alcance.

#### Requerimientos funcionales

- M11-RF1. El servicio deberá exponer un endpoint que reciba la consulta del paciente en texto y devuelva la respuesta en texto.
- M11-RF2. El servicio deberá responder en español sobre estudios genéticos: qué es un exoma clínico, cómo es el proceso del estudio (extracción, traslado, análisis), qué son las patologías lisosomales (Fabry, Pompe, mucopolisacaridosis tipo 1, Gaucher y ASMD) y qué significan términos del resultado (variante, patogénica, benigna, VUS) **[supuesto]**.
- M11-RF3. Ante una consulta fuera del alcance, el servicio deberá indicar que solo responde sobre estudios genéticos y no inventar una respuesta.
- M11-RF4. El servicio no deberá dar un diagnóstico, interpretar el resultado individual de un paciente ni recomendar tratamientos. En esos casos deberá sugerir hablar con su médico tratante, sin derivar a una persona del laboratorio (escenario 40) **[supuesto]**.
- M11-RF5. Las respuestas deberán basarse en una base de conocimiento curada. Si no hay información suficiente, el servicio deberá decirlo en lugar de responder sin sustento **[supuesto]**.
- M11-RF6. El servicio deberá aceptar un identificador de conversación opcional para mantener el contexto de los mensajes anteriores **[supuesto]**.
- M11-RF7. El servicio no deberá recibir ni guardar datos personales identificables del paciente **[supuesto]**.
- M11-RF8. Si el servicio no está disponible, deberá devolver un error claro para que la aplicación consumidora informe que el chatbot no responde (escenario 40).
- M11-RF9. El servicio deberá limitar el largo de la consulta y la cantidad de consultas por consumidor.
- M11-RF10. El servicio deberá registrar las consultas y las respuestas, sin datos personales, para evaluar su calidad **[supuesto]**.
- M11-RF11. El servicio deberá tener documentada su API (formato de pedido y respuesta, errores y ejemplo de uso) para los grupos consumidores.
- M11-RF12. Nuestra plataforma deberá incluir una ventana de chat en la vista del paciente, reutilizable por otros grupos **[supuesto]**.
- M11-RF13. El servicio deberá poder desplegarse por separado de la plataforma, para que los demás grupos lo consuman aunque la plataforma no esté activa.

#### Notas

- Canal (plataforma o WhatsApp): pendiente P10. Se arranca por la plataforma.
- La tecnología, el costo y la fuente de la base de conocimiento están pendientes (decisión 6).
- El chatbot no es un canal de soporte: no deriva a una persona, por indicación del PO.

#### Permisos

- Lo consulta el paciente. Los otros grupos acceden por la API, con el esquema de autenticación pendiente (decisión 7).

---

## Requisitos técnicos y pautas de trabajo

- Acceso desde computadora y celular, con diseño responsive.
- Los datos genéticos son sensibles: sesiones con vencimiento, contraseñas con hash, acceso a cada dato solo para el rol que corresponde y registro de quién abrió cada estudio **[supuesto]**.
- Cada estudio se identifica por un estado único del ciclo de vida: Creado, Pagado o Autorizado, Turno sacado, Listo para retirar, En camino al laboratorio central, En laboratorio central, En viaje a Corea, En el área de bioinformática, En análisis por un bioinformático y Resultado disponible. Pompe urgente es una marca de prioridad independiente y Rechazado es el resultado negativo de una autorización.
- Vocabulario del LEL sin sinónimos en pantallas, mails y documentos.
- Queda fuera del alcance: pago real (se integraría Mercado Pago), consulta automática a la obra social, incidentes de transporte y firma digital del consentimiento.
- Lo que no esté en este documento se evalúa como pedido nuevo de la cátedra.
