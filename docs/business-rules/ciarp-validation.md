# Reglas de Negocio: Validacion de CIARP

## Objetivo

Definir, en un solo lugar, las reglas que determinan:

- Cuando un archivo CIARP se rechaza (error)
- Cuando genera advertencia
- Que se guarda del archivo cargado

## Alcance

Aplica al flujo de carga de CIARP (`/submit/ciarp`): `ciarp_service`, `ciarp_validator`, el reporte PDF
(`generate_quality_report_ciarp`) y el Excel anotado (`ciarp_validado.xlsx`).

El CIARP se valida de forma independiente: ningun dato se toma de un archivo de Staff cargado antes.

## Regla de decision por severidad

1. Error: bloquea la aceptacion del archivo. Un solo error rechaza el archivo.
2. Advertencia: no bloquea, pero se reporta en el PDF y en el Excel anotado.

## Columnas de la plantilla

El archivo debe traer estas columnas (sin importar tildes, mayusculas ni espacios alrededor); si falta alguna, se
rechaza con "Columnas faltantes" antes de revisar filas:

`identificación`, `año`, `título`, `idioma`, `revista`, `editorial`, `doi`, `issn`, `isbn`, `volumen`, `issue`,
`primera_página`, `última_página`, `pais_producto`, `entidad_premiadora`, `ranking`.

- Una columna sin nombre con datos es error. Cualquier otra columna adicional se ignora.
- `código_unidad_académica`, `código_subunidad_académica` y `tipo_documento` ya no hacen parte de la plantilla: si el
  archivo las trae (con o sin tildes, mayusculas o espacios), se eliminan al leerlo. No generan errores ni
  advertencias, no aparecen en el Excel anotado y no se guardan.

## Campos obligatorios (vacio = error)

- `identificación`
- `año`
- `título`

Si la columna esta vacia en **todas** las filas, se reporta un unico error para la columna:
"La columna X es obligatoria y está vacía en todas las filas (N). Cada archivo debe incluirla completa; no se toma del
archivo de Staff."

Si esta vacia solo en algunas filas, hay un error por fila ("Campo obligatorio vacío"), agrupado en el PDF con el total
de filas y ejemplos con el numero de fila de Excel.

Un campo vacio genera un solo error: los demas validadores ignoran las celdas vacias.

## Campos con validacion de formato (invalido = error)

- `año`: numerico (se acepta `2020`, `"2020"` o `2020.0`) y no posterior al año actual.

## Advertencias

- `idioma` fuera de ISO 639-1 (dos letras, ej. `es`, `en`): una por fila.
- `pais_producto` fuera de ISO 3166-1 alfa-2 (dos letras, ej. `CO`, `US`): una por fila.
- `ranking` es opcional: si esta vacio, una sola advertencia para la columna ("La columna ranking está vacía en N
  filas"), nunca un error.

Las unidades academicas (codigos y nombres) no hacen parte del CIARP; sus reglas solo aplican a Staff.

## Duplicados

- Dos filas son duplicadas si repiten exactamente los valores de todas las columnas de la plantilla presentes en el
  archivo. Son informativos: no rechazan el archivo.
- El PDF indica el recuento, las columnas comparadas y ejemplos con columnas del CIARP (fila de Excel,
  `identificación`, `año`, `título`, `doi`).

## Reporte PDF

- Errores agrupados por columna y detalle, con el numero de filas y filas de ejemplo de Excel ("Todas" para un error
  de columna).
- Advertencias agrupadas por columna, detalle y valor, con el numero de filas, como en Staff.

## Archivo guardado

- Sin columnas eliminadas, se guarda el archivo cargado tal cual.
- Si traia alguna columna eliminada (`código_unidad_académica`, `código_subunidad_académica`, `tipo_documento`), se
  guarda una copia procesada sin esas columnas.

## Practica recomendada en el repositorio

- Actualizar este documento junto con cualquier cambio en `ciarp_validator`, `ciarp_required_fields_validator` o los
  validadores compartidos con Staff (`year_validator`).

## Historial

- 2026-11-09: Primera version formal del documento para CIARP: `tipo_documento` fuera de la plantilla,
  `código_unidad_académica` opcional, errores y advertencias de columnas vacias agrupados por columna, PDF con
  advertencias detalladas y criterio de duplicados.
- 2026-11-11: `código_unidad_académica` y `código_subunidad_académica` salen de la plantilla, como `tipo_documento`:
  se eliminan al leer el archivo, sin validaciones, y no se guardan.
