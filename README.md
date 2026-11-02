# Normalizador de transacciones

## Ejecutar el programa

### Interfaz web

Instala las dependencias y ejecuta Flask desde la carpeta del proyecto:

```powershell
python -m pip install -r .\requirements.txt
python .\app.py
```

Después abre [http://127.0.0.1:5000](http://127.0.0.1:5000) y carga un archivo JSON con un arreglo de transacciones. El tamaño máximo permitido es 10 MB.

**Aplicación desplegada:** [Abrir el sitio](URL_DE_DESPLIEGUE)

Reemplaza `URL_DE_DESPLIEGUE` con el enlace público cuando despliegues la aplicación.

### Interfaz de línea de comandos

La CLI no requiere Flask. Puedes pasar la ruta del JSON como argumento:

```powershell
python .\normalizador_transacciones.py ".\Transacciones ejemplo\transacciones_mixtas.json"
```

O ejecutar el programa sin argumentos para que solicite la ruta:

```powershell
python .\normalizador_transacciones.py
```

## Descripción

El proyecto lee transacciones JSON de distintas fuentes, valida sus campos y transforma los registros válidos a un esquema común. La interfaz web permite consultar las transacciones normalizadas, filtrarlas por estado, moneda y fuente, revisar métricas y examinar los registros rechazados.

La normalización reconoce tres formatos:

- **Fuente A:** `id`, `amount`, `currency`, `timestamp` y `status`.
- **Fuente B:** `transaction_id`, `total`, `currency_code`, `created_at` y `state`. El monto de entrada se interpreta en unidades menores y se convierte a unidades principales.
- **Fuente C:** `ref`, `amount`, `date` y `result`. Cuando falta el código de moneda, puede inferirse de los símbolos `€`, `$` y `£`.

Los registros válidos se expresan con `id`, `amount`, `currency`, `timestamp`, `status` y `source`. Los registros inválidos se conservan aparte con su posición, contenido original y motivos de rechazo. La interfaz web ofrece acciones para marcarlos, separarlos o descartarlos; los cambios se reflejan en la descarga. La descarga web incluye transacciones válidas y los registros inválidos clasificados. La exportación de la CLI contiene únicamente transacciones válidas.

## Archivos de ejemplo

En [`Transacciones ejemplo`](./Transacciones%20ejemplo/) se incluyen:

- [`transacciones_formato_correcto.json`](./Transacciones%20ejemplo/transacciones_formato_correcto.json): transacciones válidas en el formato de la fuente A.
- [`transacciones_para_normalizar.json`](./Transacciones%20ejemplo/transacciones_para_normalizar.json): formatos de las fuentes B y C que requieren transformación.
- [`transacciones_mixtas.json`](./Transacciones%20ejemplo/transacciones_mixtas.json): registros válidos e inválidos para probar la validación y las acciones web.

## Estructura principal

- `normalizador_transacciones.py`: lectura, validación, normalización, métricas e interfaz CLI.
- `app.py`: aplicación web Flask.
- `templates/index.html`: plantilla de la interfaz.
- `static/js/app.js`: filtros, carga, acciones de registros inválidos y descarga.
- `static/js/tailwind-config.js`: configuración de Tailwind.
- `static/css/app.css`: estilos adicionales.
- `requirements.txt`: dependencias de la interfaz web.
- `instruction.md`: requisitos y reglas detalladas del proyecto.
