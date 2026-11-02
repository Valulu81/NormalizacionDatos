# Sistema de normalización de transacciones

## Descripción de la actividad

Desarrolla un sistema en Python que lea transacciones de distintas fuentes, las transforme a un modelo común y permita explorarlas mediante una interfaz interactiva. El proyecto debe demostrar:

- Un modelo normalizado y consistente.
- Reglas explícitas de transformación y validación.
- Métricas que ayuden a entender los datos procesados.
- Una interfaz interactiva; imprimir un resumen sin permitir consultas no es suficiente.

La CLI usa la biblioteca estándar de Python. La interfaz web opcional usa Flask.

### Formato de entrada

El archivo de entrada debe ser JSON con un arreglo de objetos. Cada objeto puede usar uno de estos formatos:

```json
[
  {
    "id": "tx_001",
    "amount": "100.50",
    "currency": "USD",
    "timestamp": "2025-03-10 14:22:00",
    "status": "completed"
  },
  {
    "transaction_id": 204,
    "total": 10050,
    "currency_code": "usd",
    "created_at": "10/03/2025 14:22",
    "state": "OK"
  },
  {
    "ref": "A-77",
    "amount": "€99,99",
    "date": "2025-03-10T14:22:00Z",
    "result": "success"
  }
]
```

## Requerimientos funcionales de normalización y validación

### Normalización

Cada registro válido debe producir una transacción con este esquema:

```json
{
  "id": "string",
  "amount": 99.99,
  "currency": "USD",
  "timestamp": "2025-03-10T14:22:00Z",
  "status": "SUCCESS",
  "source": "source_a"
}
```

Reglas de transformación implementadas:

- La fuente A usa `id`, `amount`, `currency`, `timestamp` y `status`.
- La fuente B usa `transaction_id`, `total`, `currency_code`, `created_at` y `state`. `total` se interpreta como unidades menores (centavos) y se divide entre 100.
- La fuente C usa `ref`, `amount`, `date` y `result`. Si no hay campo de moneda, los símbolos `€`, `$` y `£` permiten inferir EUR, USD y GBP.
- Los montos se procesan con `Decimal`. Para cadenas, una coma sin punto es el separador decimal (`99,99`); si aparecen ambos separadores, el último se interpreta como decimal y el otro como separador de miles. Los símbolos de moneda admitidos son `€`, `$` y `£`.
- Las monedas se validan como códigos de tres letras y se convierten a mayúsculas.
- Los estados se convierten a `SUCCESS`, `FAILED` o `PENDING`. Se reconocen sin distinguir mayúsculas: `completed`, `success`, `ok`; `failed`, `error`, `declined`; y `pending`, `processing`, `created`.
- Las fechas ISO 8601, `YYYY-MM-DD HH:MM:SS`, `DD/MM/YYYY HH:MM` y fechas `YYYY-MM-DD` son aceptadas. Las fechas sin zona horaria se interpretan como UTC; la salida siempre usa ISO 8601 con `Z` para UTC.
- El identificador debe ser texto no vacío o un entero (no booleano). El monto debe ser numérico, finito y mayor que cero.

### Validación y métricas

- El archivo debe contener un arreglo JSON. Cada elemento que no sea un objeto, no corresponda a una fuente reconocida o no cumpla todas las validaciones se registra como inválido, con su posición, fuente identificada (si es posible), registro original y razones de rechazo.
- Ningún registro inválido se incluye entre las transacciones normalizadas. Se conserva en una lista separada durante la ejecución para que el usuario pueda inspeccionarlo.
- Un fallo de lectura, codificación UTF-8 o sintaxis JSON se informa explícitamente; no se trata como un archivo vacío.
- Las métricas muestran total procesado, total válido e inválido, conteo por estado y suma de montos válidos por moneda.

## Interfaz interactiva

Inicia la CLI desde esta carpeta:

```powershell
python .\normalizador_transacciones.py .\transacciones.json
```

Sin argumento, el programa solicitará la ruta al archivo JSON. Después de cargarlo, el menú permite:

1. Listar transacciones normalizadas.
2. Filtrar por estado, moneda o fuente.
3. Consultar métricas.
4. Inspeccionar registros inválidos y sus razones.
5. Exportar las transacciones válidas como JSON.
0. Salir.

La exportación contiene únicamente transacciones válidas, en el esquema común. Si se indica un nombre de archivo sin extensión, se agrega `.json`.

## Interfaz web opcional

Instala Flask y ejecuta la interfaz desde esta carpeta:

```powershell
python -m pip install -r .\requirements.txt
python .\app.py
```

Abre `http://127.0.0.1:5000`, carga un archivo `.json` con un arreglo de registros y selecciona **Cargar y normalizar**. La página muestra las transacciones válidas, permite filtrarlas por estado, moneda y fuente, presenta las métricas y conserva una tabla separada con los registros inválidos y sus motivos. El tamaño máximo de carga es 10 MB.

Los archivos de la interfaz web se organizan así: `templates\index.html` contiene la estructura HTML, `static\js\app.js` contiene la interacción, `static\js\tailwind-config.js` contiene la configuración de Tailwind y `static\css\app.css` contiene los estilos propios adicionales.

En la tabla de registros inválidos, las acciones actualizan la vista y la siguiente descarga:

- **Marcar** identifica el registro como revisado; sigue en la lista y se incluye en `invalid_records.marked`.
- **Separar** lo mueve a la sección de registros separados y se incluye en `invalid_records.separated`.
- **Descartar** lo mueve a la sección de descartados y lo excluye de las listas de registros inválidos descargadas. Puede restaurarse antes de descargar.
- Se puede deshacer **Marcar**, **Separar** y **Descartar** mientras la página siga abierta.

La descarga web es un objeto JSON con `transactions` (solo transacciones válidas), `invalid_records` (arreglos `pending`, `marked` y `separated`, con posición, fuente, `original_json` y motivos) y `discarded_count`. La exportación de la CLI permanece como un arreglo que contiene únicamente transacciones válidas.

Se incluyen tres archivos de ejemplo:

- `transacciones_formato_correcto.json`: registros válidos en el formato de la fuente A.
- `transacciones_para_normalizar.json`: registros válidos de las fuentes B y C que requieren transformación.
- `transacciones_mixtas.json`: registros válidos y casos inválidos para inspeccionar la separación y los motivos de rechazo.
