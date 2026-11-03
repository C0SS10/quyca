# Reglas de negocio: validación del archivo de proyectos

Cómo valida `POST /submit/project` el archivo de proyectos que envían las instituciones. El formato que reciben las instituciones es el documento *Formato para la obtención de información de Proyectos Institucionales, versión 1.0*. Las columnas, los campos obligatorios y los valores admitidos están en `quyca/constants/project_file_schema.py`.

El endpoint **solo valida y devuelve un reporte**: no guarda el archivo ni escribe en la base.

## Envío

- Requiere una sesión activa y el token CSRF, igual que las demás cargas. Sin sesión responde 401; con la cuenta desactivada, 403.
- El archivo va en el campo `file` de un formulario `multipart/form-data`.
- **Solo se admite `.xlsx`.** El documento del formato dice ".xlsx o .xls", pero leer `.xls` exige una dependencia que interpreta el formato binario antiguo, así que se decidió no admitirlo, igual que en staff y CIARP. Un `.xls` recibe un mensaje que pide guardarlo como `.xlsx`. **Hay que corregir el documento del formato.**
- Solo se lee la primera hoja. Si hay más, se reporta una advertencia.

## Límites

Protegen al servidor de archivos enormes o armados para inflarse al abrirlos. Están en `quyca/constants/project_file_schema.py`.

| Límite | Valor | Respuesta |
|---|---|---|
| Tamaño del envío | 10 MB | 413, sin leer el archivo |
| Contenido descomprimido (un `.xlsx` es un zip) | 100 MB | 400 |
| Filas con datos | 20 000 | 400 |
| Problemas listados en el reporte | 500 | 200, con `issues_truncated: true` y los conteos completos |

Cualquier archivo que no se pueda leer (vacío, dañado, de otro tipo o con XML malicioso) responde **400** con el motivo, nunca 500. El lector de XML no resuelve entidades externas y corta la expansión de entidades: un archivo no puede leer archivos del servidor ni agotar su memoria.

## Encabezados

Se reconocen aunque cambien las mayúsculas, las tildes, los espacios o lleven el `*` con el que el documento marca los obligatorios. Por ejemplo, `Código Proyecto*` es `codigo_proyecto`.

| Situación | Severidad |
|---|---|
| Falta una columna obligatoria | Error |
| Falta `resumen` | Advertencia |
| Una columna aparece dos veces | Error |
| Columna que no es del formato | Advertencia: se ignora |
| La primera fila no tiene encabezados | 400 |

Si hay errores de estructura, las filas no se validan y `total_projects` es `null`.

## Valores

Las filas en blanco se ignoran, y los números de fila del reporte son los de Excel.

| Tipo | Se acepta | Se rechaza |
|---|---|---|
| Catálogo (`tipo_proyecto`, `estado`) | El valor sin importar mayúsculas, tildes ni espacios extra | Valores fuera del catálogo |
| Fecha | Celda con formato de fecha, o texto `DD/MM/YYYY` | `2022-05-12`, `12/05/22`, fechas imposibles y números sin formato de fecha |
| Dinero (COP) | Entero, o texto con solo dígitos | `$ 50.000.000`, separadores, decimales y negativos |
| Documento | Un solo valor sin espacios ni separadores | `123 456`, `123;456` |
| ROR | `03bp5hc83` o `https://ror.org/03bp5hc83` | Cualquier otra cosa |
| ROR o Wikidata | Lo anterior, o `Q12345` y sus URL de Wikidata | Nombres de entidades |
| GeoNames | El número, o la URL de GeoNames | Nombres de lugares |

Las columnas de lista (`investigadores_ids`, `fuente_financiacion_ids`, etc.) se separan con `;`. Cada valor inválido se reporta por separado, y los repetidos generan una advertencia.

## Reglas entre campos

| Regla | Severidad |
|---|---|
| `fecha_fin` anterior a `fecha_inicio` | Error |
| Proyecto `finalizado` sin `fecha_fin` (si la columna existe) | Advertencia |
| Proyecto de `regalías` sin `codigo_bpin` | Advertencia |
| El investigador principal también está en `investigadores_ids` | Advertencia |
| `valor_total` distinto de `valor_especie_total + valor_fresco_total` (si los tres tienen valor) | Advertencia |

## Proyectos en varias filas

Un proyecto puede repetirse en varias filas con el mismo `codigo_proyecto` para agregar investigadores o fuentes. En ese caso:

- Las columnas de lista pueden variar entre filas.
- Las demás columnas deben coincidir: un valor distinto es un error que señala la fila de referencia.
- `P1` escrito como número y como texto es el mismo proyecto.
- `total_projects` cuenta los códigos distintos.

## Reporte

```json
{
  "data": {
    "schema_version": "1.0",
    "valid": false,
    "total_rows": 2,
    "total_projects": 2,
    "errors_count": 1,
    "warnings_count": 0,
    "issues_truncated": false,
    "issues": [
      {"row": 3, "column": "valor_total", "code": "invalid_money", "severity": "error",
       "message": "Debe contener solo números, sin signos de moneda ni separadores de miles (ej. 50000000).",
       "value": "$ 5.000"}
    ]
  }
}
```

`valid` es `true` cuando no hay errores; las advertencias no lo cambian. Los problemas vienen ordenados por fila (primero los del archivo, que no tienen fila) y luego por columna.
