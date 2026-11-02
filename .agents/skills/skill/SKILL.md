---
name: skill
description: Aplica estas reglas al desarrollar o modificar este proyecto.
---
# Directrices de implementación: normalización de transacciones

Aplica estas reglas al desarrollar o modificar este proyecto:

## Modularidad y legibilidad

- Mantén separadas la lectura del archivo, la detección de fuente, la normalización, la validación, las métricas y la interacción CLI en funciones con responsabilidades concretas.
- Usa nombres descriptivos, anotaciones de tipos y estructuras de datos explícitas. Evita lógica de negocio dentro de los menús.
- Limita las dependencias a la biblioteca estándar salvo que el usuario autorice otra cosa.
- No cambies silenciosamente el esquema de salida ni las reglas documentadas en `instruction.md`.

## Datos inválidos: reglas estrictas

- Valida cada campo requerido antes de crear una transacción normalizada.
- Rechaza y separa el registro completo si su forma no corresponde a una fuente conocida o si falta/es inválido cualquier dato requerido. Conserva su posición, contenido original y motivos concretos; nunca sustituyas datos inválidos por valores predeterminados que parezcan válidos.
- No incluyas registros rechazados en listados normalizados, métricas válidas ni exportaciones.
- Rechaza identificadores vacíos o de tipos no admitidos, montos no numéricos, no finitos o no positivos, monedas con formato incorrecto, estados desconocidos y fechas imposibles o no reconocidas.
- Informa explícitamente errores de archivo, UTF-8 y JSON. No conviertas excepciones de lectura o parseo en resultados vacíos, ni uses capturas amplias que oculten fallos.
- Si una regla nueva cambia qué datos se aceptan o rechazan, actualiza `instruction.md` y las pruebas relacionadas.

## JSON, precisión y tipos

- Trata el contenido externo como no confiable: comprueba la estructura raíz y el tipo de cada registro antes de acceder a sus campos.
- Usa el módulo `json` de la biblioteca estándar y mensajes claros para JSON inválido. Rechaza constantes JSON no estándar como `NaN` e `Infinity`.
- Evita `float` para cálculos monetarios; convierte los valores a `Decimal`, verifica que sean finitos y mantén la precisión hasta la presentación o exportación.
- Normaliza los códigos de moneda y estados de forma explícita. Serializa solo los campos del esquema acordado y asegúrate de que los valores de salida sean JSON válidos.
- No uses booleanos como números o identificadores. No agregues conversiones implícitas que puedan ocultar datos malformados.
- Conserva las anotaciones de tipo y evita `Any`, casts innecesarios y acceso a claves sin validación en la lógica de negocio.

## Que no hacer 
- No ignores errores de lectura o parseo de archivos.
- No ignores errores de validación de datos.
- No ignores errores de conversión de tipos.
- No ignores errores de normalización de datos.
- No ignores errores de exportación de datos.
- No ignores errores de interacción con el usuario.
