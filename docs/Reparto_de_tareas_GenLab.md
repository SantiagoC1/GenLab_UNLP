# Reparto de tareas entre 3 integrantes

> Acompaña a `Especificacion_requerimientos_GenLab.md`. Cada tarea sale de un requerimiento de esa especificación, así que se puede rastrear de punta a punta. Los nombres A, B y C se reemplazan por los de ustedes.

## Cómo se repartió

- Se sacaron los módulos que construyen otros grupos (familiograma, SNOMED, cupones, CDSS, Apigen, obras sociales, avisos, optimización de recorrido y FedEx). De cada uno nos queda solo el cliente que lo consume.
- Cada tarea tiene un **puntaje de esfuerzo relativo** de 1 a 5. Es una estimación inicial (incluye interfaz, lógica, pruebas básicas y la parte de integración), no horas. Ajusten los puntos si alguno les parece mal: el reparto se recalcula con la tabla.
- Las áreas se agruparon por flujo (un mismo integrante sigue un estudio de un estado al siguiente), para que cada uno entienda su tramo completo y haya pocas dependencias cruzadas.
- El **chatbot** se dividió en tres partes (contenido y contrato, servicio, interfaz y despliegue) y cada integrante tiene una.
- La documentación obligatoria de la cátedra también se repartió.

## Resumen de carga

| Integrante | Foco | Plataforma | Chatbot | Total |
|---|---|---|---|---|
| Integrante A | Núcleo, acceso y consulta médica, más contenido y contrato del chatbot | 38 | 6 | 44 |
| Integrante B | Presupuesto, pago, cupones y turnos, más el servicio del chatbot | 37 | 8 | 45 |
| Integrante C | Logística, bioinformática y avisos, más la interfaz, pruebas y despliegue del chatbot | 35 | 8 | 43 |

Total: 132 puntos, unos 44 por persona. La diferencia máxima entre integrantes es de 2 puntos.

## Detalle por integrante

### Integrante A: Núcleo, acceso y consulta médica, más contenido y contrato del chatbot (44 puntos)

**Plataforma**

| ID | Tarea | Escenarios | Puntos |
|---|---|---|---|
| T1 | Arquitectura base: repositorio, base de datos, API, despliegue, modelo de estados del estudio | todos | 5 |
| T2 | Interfaz base: layout, navegación por rol, estilos, componentes comunes | todos | 3 |
| T4 | Documentación: especificación de requerimientos del sistema y glosario | todos | 2 |
| 1.1 | Registrarse por autoalta | 1 | 2 |
| 1.2 | Dar de alta a un usuario (administrador general) | 2 | 2 |
| 1.3 | Activar la cuenta del paciente | 3 | 2 |
| 1.4 | Ingresar con código por mail y bloqueo a los 5 intentos | 4 | 4 |
| 2.1 | Dar de alta una patología lisosomal | 5 | 2 |
| 2.2 | Modificar los síntomas de una patología | 6 | 1 |
| 3.1 | Buscador de síntomas con SNOMED (cliente del módulo adicional 2) | 7 | 3 |
| 3.2 | Familiograma: carga de familiares y cliente del módulo adicional 1 | 8 | 3 |
| 3.3 | Dar de alta al paciente, con regla de correspondencia clínica y cliente CDSS | 9 | 5 |
| 3.4 | Dar de alta el estudio, con genes de Apigen y marca Pompe urgente | 10 | 4 |

**Chatbot**

| ID | Tarea | Escenarios | Puntos |
|---|---|---|---|
| CB1 | Chatbot: alcance, contrato de la API y acuerdo con los grupos consumidores | MA8 | 2 |
| CB2 | Chatbot: base de conocimiento sobre estudios genéticos y patologías lisosomales | MA8 | 4 |

### Integrante B: Presupuesto, pago, cupones y turnos, más el servicio del chatbot (45 puntos)

**Plataforma**

| ID | Tarea | Escenarios | Puntos |
|---|---|---|---|
| T3 | Datos de ejemplo y recorrido de demostración para el coloquio | todos | 2 |
| T5 | Documentación: casos de prueba (caja negra) de los módulos propios | todos | 2 |
| 4.1 | Emitir el presupuesto | 11 | 2 |
| 4.2 | Elegir la cobertura por obra social (cliente del módulo adicional 6) | 12 | 3 |
| 4.3 | Pagar el estudio de forma particular y registro financiero | 13 | 3 |
| 4.4 | Aplicar un cupón de descuento (cliente del módulo adicional 3) | 14 | 2 |
| 5.1 | Generar cupones de descuento | 15 | 2 |
| 5.2 | Asignar cupones al médico tratante | 16 | 1 |
| 5.3 | Asignar un cupón al paciente | 17 | 1 |
| 4.5 | Registrar la autorización de la obra social | 18 | 2 |
| 4.6 | Solicitar la reautorización con una demanda | 19 | 2 |
| 6.1 | Sacar turno: mapa de laboratorios y turneros generados por regla | 20 | 5 |
| 6.2 | Descargar la orden de extracción y el consentimiento informado (PDF) | 21 | 2 |
| 6.3 | Cancelar el turno de extracción | 22 | 1 |
| 6.4 | Registrar una inasistencia y reprogramar | 23 | 2 |
| 6.5 | Recibir la notificación de la muestra (endpoint y simulador de Telegram) | 24 | 3 |
| 6.6 | Solicitar el remuestreo | 25 | 2 |

**Chatbot**

| ID | Tarea | Escenarios | Puntos |
|---|---|---|---|
| CB3 | Chatbot: servicio de consulta, integración con el modelo de lenguaje y control de alcance | MA8 | 5 |
| CB4 | Chatbot: sesiones, límites de uso, manejo de errores y registro | MA8 | 3 |

### Integrante C: Logística, bioinformática y avisos, más la interfaz, pruebas y despliegue del chatbot (43 puntos)

**Plataforma**

| ID | Tarea | Escenarios | Puntos |
|---|---|---|---|
| T6 | Documentación: arquitectura y diseño (clases, estados, integraciones) | todos | 1 |
| 7.1 | Orden del día del transportista (cliente del módulo adicional 9) | 26 | 3 |
| 7.2 | Retirar muestras en cada parada | 27 | 2 |
| 7.3 | Entregar las muestras y armar lotes de 10 | 28 | 3 |
| 7.4 | Solicitar el permiso del Ministerio de Salud (CSV y API simulada) | 29 | 2 |
| 7.5 | Cerrar anticipadamente un lote por Pompe urgente | 30 | 1 |
| 7.6 | Programar el retiro con FedEx (cliente del módulo adicional 10) | 31 | 3 |
| 7.7 | Registrar el retiro del lote y pasar a En viaje a Corea | 32 | 2 |
| 7.8 | Consultar la ubicación de una muestra en traslado [deseo] | 33 | 2 |
| 8.1 | Cargar los datos crudos de un estudio | 34 | 2 |
| 8.2 | Tomar un estudio para su análisis | 35 | 2 |
| 8.3 | Registrar variantes (Apigen) y finalizar con el PDF del resultado | 36 | 4 |
| 8.4 | Consultar y descargar el resultado (médico y paciente) | 37, 38 | 2 |
| 8.5 | Solicitar el reanálisis de un estudio | 39 | 2 |
| 9.1 | Avisos dentro de la plataforma y cliente del módulo adicional 7 | 41 | 3 |
| 9.2 | Integrar el chatbot en la vista del paciente | 40 | 1 |

**Chatbot**

| ID | Tarea | Escenarios | Puntos |
|---|---|---|---|
| CB5 | Chatbot: ventana de chat reutilizable para los consumidores | MA8 | 3 |
| CB6 | Chatbot: pruebas con preguntas dentro y fuera de alcance, y documentación de uso | MA8 | 3 |
| CB7 | Chatbot: despliegue independiente y monitoreo | MA8 | 2 |

## División del chatbot

| Parte | Responsable | Qué entrega | Se necesita de |
|---|---|---|---|
| Contenido y contrato (CB1, CB2) | A | Documento con el alcance, el contrato de la API acordado con los grupos consumidores, y la base de conocimiento curada | Cátedra, para validar el alcance |
| Servicio (CB3, CB4) | B | Endpoint de consulta, integración con el modelo de lenguaje, control de alcance, sesiones, límites y errores | Contrato de A y base de conocimiento de A |
| Interfaz, pruebas y despliegue (CB5, CB6, CB7) | C | Ventana de chat, batería de pruebas, documentación de uso y despliegue independiente | Servicio de B funcionando |

Orden recomendado: A cierra el contrato en la primera semana para que B y C no esperen, y B publica una versión mínima (respuesta fija) enseguida para que C pueda desarrollar la interfaz contra ella.

## Dependencias entre integrantes

| Quién entrega | Qué | A quién | Cuándo conviene |
|---|---|---|---|
| A | Arquitectura base, autenticación, roles, estados del estudio y navegación (T1, T2, 1.4) | B y C | Semana 1 |
| A | Alta de paciente y de estudio (3.3, 3.4), que crea los datos que usan todos | B y C | Semana 2 |
| B | Estudio Pagado o Autorizado (4.3, 4.5) y turno sacado, que habilita la logística | C | Semana 3 |
| B | Notificación de muestra Listo para retirar (6.5), que alimenta la orden del día | C | Semana 3 |
| C | Interfaz de avisos (9.1), que todos usan para notificar | A y B | Semana 2 |
| C | Interfaz de chat (CB5), que se muestra en la vista del paciente | B | Semana 5 |

Mientras una dependencia no llega, cada uno trabaja con datos de ejemplo (T3) o con el simulador del adaptador.

## Orden sugerido hasta el coloquio

Es una propuesta [supuesto]. El coloquio es el 7 de diciembre.

| Semana | A | B | C |
|---|---|---|---|
| 1 (desde el 20/10) | T1, T2, 1.1 a 1.4, CB1 | Diseño de datos de turnos, 4.1 | Diseño de lotes y estados logísticos, 9.1 |
| 2 (desde el 27/10) | 2.1, 2.2, 3.1, 3.3 | 4.2, 4.3, 4.4, CB3 versión mínima | 9.1, 7.1, 7.2, CB5 sobre la versión mínima |
| 3 (desde el 3/11) | 3.2, 3.4, CB2 | 4.5, 4.6, 5.1 a 5.3, 6.1 | 7.3, 7.4, 7.5, 8.1 |
| 4 (desde el 10/11) | T4, CB2 | 6.2 a 6.6, CB4 | 7.6, 7.7, 8.2, 8.3 |
| 5 (desde el 17/11) | Integración y correcciones de su tramo | T3, CB3 completo | 8.4, 8.5, 9.2, CB5 completo |
| 6 (desde el 24/11) | Pruebas de punta a punta | T5, correcciones | T6, CB6, CB7, 7.8 si hay tiempo |
| 7 (hasta el 7/12) | Ensayo del coloquio, sin funcionalidades nuevas | | |

La tarea 7.8 (ubicación de la muestra) y el dictado por voz de 3.3 son deseos del PO: si el tiempo se acorta, son lo primero que se recorta.

## Acuerdos con otros grupos

Cada integrante cierra los contratos de los módulos que consume en su tramo:

| Módulo | Contrato a cerrar | Responsable |
|---|---|---|
| SNOMED, CDSS, Apigen, Familiograma | Formato de entrada y salida, paginación, errores | A |
| Obras sociales, Cupones | Formato, y la definición de si el administrativo o la web del grupo registra la autorización | B |
| Optimización de recorrido, FedEx, Avisos | Formato de direcciones, quién consulta a quién en FedEx, canales de aviso | C |
| Chatbot (nosotros como proveedor) | Contrato publicado para los consumidores | A |

Mientras no haya contrato cerrado, se usa el simulador del adaptador (M10-RF2).

## Reglas de trabajo

- Cada tarea termina cuando su requerimiento se cumple en pantalla, con sus excepciones y con casos de prueba escritos.
- Los cambios de estado del estudio siguen el catálogo de la especificación. Nadie agrega estados sin avisar al resto.
- El vocabulario de pantallas, mails y documentos es el del LEL.
- Si alguien se atrasa, se mueve una tarea completa a otro integrante y se actualiza este documento. No se divide una tarea a medias.

## Tabla completa de tareas

| ID | Tarea | Escenarios | Puntos | Responsable | Nota |
|---|---|---|---|---|---|

| T1 | Arquitectura base: repositorio, base de datos, API, despliegue, modelo de estados del estudio | todos | 5 | A | Desbloquea a los demás: entregar en la semana 1 |
| T2 | Interfaz base: layout, navegación por rol, estilos, componentes comunes | todos | 3 | A | Desbloquea a los demás: entregar en la semana 1 |
| T3 | Datos de ejemplo y recorrido de demostración para el coloquio | todos | 2 | B |  |
| T4 | Documentación: especificación de requerimientos del sistema y glosario | todos | 2 | A |  |
| T5 | Documentación: casos de prueba (caja negra) de los módulos propios | todos | 2 | B |  |
| T6 | Documentación: arquitectura y diseño (clases, estados, integraciones) | todos | 1 | C |  |
| 1.1 | Registrarse por autoalta | 1 | 2 | A |  |
| 1.2 | Dar de alta a un usuario (administrador general) | 2 | 2 | A |  |
| 1.3 | Activar la cuenta del paciente | 3 | 2 | A |  |
| 1.4 | Ingresar con código por mail y bloqueo a los 5 intentos | 4 | 4 | A |  |
| 2.1 | Dar de alta una patología lisosomal | 5 | 2 | A |  |
| 2.2 | Modificar los síntomas de una patología | 6 | 1 | A |  |
| 3.1 | Buscador de síntomas con SNOMED (cliente del módulo adicional 2) | 7 | 3 | A |  |
| 3.2 | Familiograma: carga de familiares y cliente del módulo adicional 1 | 8 | 3 | A |  |
| 3.3 | Dar de alta al paciente, con regla de correspondencia clínica y cliente CDSS | 9 | 5 | A | Incluye la configuración de estrategia del CDSS |
| 3.4 | Dar de alta el estudio, con genes de Apigen y marca Pompe urgente | 10 | 4 | A |  |
| 4.1 | Emitir el presupuesto | 11 | 2 | B |  |
| 4.2 | Elegir la cobertura por obra social (cliente del módulo adicional 6) | 12 | 3 | B |  |
| 4.3 | Pagar el estudio de forma particular y registro financiero | 13 | 3 | B |  |
| 4.4 | Aplicar un cupón de descuento (cliente del módulo adicional 3) | 14 | 2 | B |  |
| 5.1 | Generar cupones de descuento | 15 | 2 | B |  |
| 5.2 | Asignar cupones al médico tratante | 16 | 1 | B |  |
| 5.3 | Asignar un cupón al paciente | 17 | 1 | B |  |
| 4.5 | Registrar la autorización de la obra social | 18 | 2 | B |  |
| 4.6 | Solicitar la reautorización con una demanda | 19 | 2 | B |  |
| 6.1 | Sacar turno: mapa de laboratorios y turneros generados por regla | 20 | 5 | B |  |
| 6.2 | Descargar la orden de extracción y el consentimiento informado (PDF) | 21 | 2 | B |  |
| 6.3 | Cancelar el turno de extracción | 22 | 1 | B |  |
| 6.4 | Registrar una inasistencia y reprogramar | 23 | 2 | B |  |
| 6.5 | Recibir la notificación de la muestra (endpoint y simulador de Telegram) | 24 | 3 | B |  |
| 6.6 | Solicitar el remuestreo | 25 | 2 | B |  |
| 7.1 | Orden del día del transportista (cliente del módulo adicional 9) | 26 | 3 | C |  |
| 7.2 | Retirar muestras en cada parada | 27 | 2 | C |  |
| 7.3 | Entregar las muestras y armar lotes de 10 | 28 | 3 | C |  |
| 7.4 | Solicitar el permiso del Ministerio de Salud (CSV y API simulada) | 29 | 2 | C |  |
| 7.5 | Cerrar anticipadamente un lote por Pompe urgente | 30 | 1 | C |  |
| 7.6 | Programar el retiro con FedEx (cliente del módulo adicional 10) | 31 | 3 | C |  |
| 7.7 | Registrar el retiro del lote y pasar a En viaje a Corea | 32 | 2 | C |  |
| 7.8 | Consultar la ubicación de una muestra en traslado [deseo] | 33 | 2 | C |  |
| 8.1 | Cargar los datos crudos de un estudio | 34 | 2 | C |  |
| 8.2 | Tomar un estudio para su análisis | 35 | 2 | C |  |
| 8.3 | Registrar variantes (Apigen) y finalizar con el PDF del resultado | 36 | 4 | C |  |
| 8.4 | Consultar y descargar el resultado (médico y paciente) | 37, 38 | 2 | C |  |
| 8.5 | Solicitar el reanálisis de un estudio | 39 | 2 | C |  |
| 9.1 | Avisos dentro de la plataforma y cliente del módulo adicional 7 | 41 | 3 | C |  |
| 9.2 | Integrar el chatbot en la vista del paciente | 40 | 1 | C |  |
| CB1 | Chatbot: alcance, contrato de la API y acuerdo con los grupos consumidores | MA8 | 2 | A |  |
| CB2 | Chatbot: base de conocimiento sobre estudios genéticos y patologías lisosomales | MA8 | 4 | A |  |
| CB3 | Chatbot: servicio de consulta, integración con el modelo de lenguaje y control de alcance | MA8 | 5 | B |  |
| CB4 | Chatbot: sesiones, límites de uso, manejo de errores y registro | MA8 | 3 | B |  |
| CB5 | Chatbot: ventana de chat reutilizable para los consumidores | MA8 | 3 | C |  |
| CB6 | Chatbot: pruebas con preguntas dentro y fuera de alcance, y documentación de uso | MA8 | 3 | C |  |
| CB7 | Chatbot: despliegue independiente y monitoreo | MA8 | 2 | C |  |
