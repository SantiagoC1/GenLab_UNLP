# Base de conocimiento del chatbot

Cada archivo `.md` es un tema. El servicio responde solo con lo que está acá (M11-RF5).
Este README no tiene encabezado, así que el servicio lo ignora.

## Formato

```
---
tema: Nombre del tema
claves: palabras que lo identifican, separadas por espacios
fuente: de dónde sale la información
estado: borrador | validado
---
Texto en español simple, de hasta unas 120 palabras.
Cierra siempre con una frase que sugiera consultar al médico tratante.
```

## Reglas

- `tema` y `claves` son lo que más pesa en la búsqueda. Poné en `claves` los nombres con que la gente
  pregunta (siglas, sinónimos, el gen). No repitas palabras de otros temas: por ejemplo, no pongas
  "lisosomal" en el texto de una patología puntual, porque compite con el tema general.
- Texto propio, resumido de las fuentes. No se copian párrafos de papers ni de sitios.
- Nada de diagnósticos, tratamientos ni dosis. Solo información general.
- Todo texto nace como `borrador`. Pasa a `validado` cuando alguien del equipo lo revisó contra la fuente.
- Si agregás o sacás un tema, actualizá la cantidad de `tests/test_knowledge.py`.
