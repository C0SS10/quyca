# Reglas de Negocio: Validacion y Normalizacion de Staff

## Objetivo

Definir, en un solo lugar, las reglas que determinan:

- Cuando una fila se rechaza (error)
- Cuando una fila genera advertencia
- Cuando un valor se normaliza a `desconocido`
- Que campos pueden venir vacios sin penalizacion

## Alcance

Aplica al flujo de carga de Staff (`/app/submit/staff`) y a la construccion de:

- `estado_de_validacion`
- Reporte PDF de calidad
- Resumen de normalizaciones aplicadas

## Regla de decision por severidad

1. Error: bloquea la aceptacion de la fila/archivo segun el total de errores.
2. Advertencia: no bloquea, pero se reporta en Excel/PDF.
3. Normalizacion: transforma el valor para alinearlo con catalogos.

Criterio: es error lo que impide interpretar el dato (fecha imposible, documento invalido, columna obligatoria ausente);
es advertencia lo que se puede cargar pero conviene mejorar; y se acepta/normaliza lo que es solo una variante de
escritura frecuente.

## Columnas opcionales: `orcid`, `cvlac`, `scholar`

- Si la columna no existe, o existe con algunos campos vacios, no es error: se reporta una advertencia por columna
  (sin fila; el PDF muestra cuantas filas cubre).
- Si la columna existe y tiene valores, se normalizan (URL canonica de ORCID y Scholar, codigo `cod_rh` de CvLAC).
- Cuando vienen en el archivo se incluyen en el archivo normalizado y en la deteccion de duplicados, igual que
  `nombre_completo`.

## Campos siempre obligatorios (vacio = error)

- tipo_documento
- identificacion
- primer_apellido
- nombres

**## Regla especial para `nombre_completo`**

- `nombre_completo` es un campo opcional.
- Si el archivo contiene la columna `nombre_completo`, se utiliza y valida `nombre_completo` en lugar de `primer_apellido`, `segundo_apellido` y `nombres`.
- Cuando `nombre_completo` esta presente, `primer_apellido`, `segundo_apellido` y `nombres` no se revisan ni se procesan.
- Si `nombre_completo` no esta presente, se mantiene la validacion tradicional de `primer_apellido`, `segundo_apellido` y `nombres`.
- `nombre_completo` debe ser de tipo texto y no puede contener numeros.
- Si `nombre_completo` esta vacio y no se cuenta con `primer_apellido`, `segundo_apellido` y `nombres`, se genera error.

## Nombres (`nombre_completo`, `primer_apellido`, `segundo_apellido`, `nombres`)

- Se permiten letras (con tildes y diacriticos), espacios, apostrofes, guiones, puntos (`Ana M. Perez`, `Jr.`) y comas
  (`Perez Gomez, Ana Maria`).
- Digitos, simbolos (`@`, `#`, `/`, `$`...) y caracteres de control son error.
- Texto con codificacion dañada (`¿`, `�`, `Ã±` en lugar de `ñ`) es error con el mensaje "posible problema de
  codificacion".

## Unidad y subunidad academica (nombres)

- Se permiten letras, numeros, espacios y `, - : ( ) . / & '` (`Tecnologias de Informacion y Comunicaciones (TIC)`).
- El error lista los caracteres no permitidos encontrados. La codificacion dañada tiene su propio mensaje.

## Tipo de documento e identificacion

- Valores admitidos: cedula de ciudadania, cedula de extranjeria, documento extranjero y pasaporte.
- Equivalencias: `CC` → cedula de ciudadania; `CE`, `documento de extranjeria`, `doc. extranjeria` → cedula de
  extranjeria; `DE`, `D.E.`, `D.E` → documento extranjero; `PS`, `PA`, `P.A.`, `passport` → pasaporte.
- Un tipo no reconocido es error y el mensaje lista los valores admitidos.
- Una cedula (CC/CE) con letras sigue siendo error, con la sugerencia de cambiar el tipo a documento extranjero o
  pasaporte.
- La identificacion de un documento extranjero solo admite letras y numeros, hasta 17 caracteres (campo alfanumerico
  de 17 del anexo tecnico PAI230 de MinEducacion para docentes, directivos y personal administrativo). Puntos,
  guiones o espacios son error.

## Campos con validacion de formato (invalido = error)

- identificacion
- fecha_nacimiento
- fecha_inicial_vinculacion
- fecha_final_vinculacion
- primer_apellido
- segundo_apellido
- nombres
- nombre_completo
- codigo_unidad_academica
- unidad_academica

## Campos fuera de catalogo (advertencia + mapeo a desconocido)

Si el campo viene vacio, se mantiene vacio. Solo se mapea a `desconocido` cuando tiene valor no vacio y no pertenece al catalogo.

- nivel_academico
- tipo_contrato
- jornada_laboral
- categoria_laboral
- sexo
- fecha_nacimiento (casos no catalogables de tipo "sin informacion")
- fecha_inicial_vinculacion (casos no catalogables de tipo "sin informacion")
- fecha_final_vinculacion (casos no catalogables de tipo "sin informacion")

## Campos fuera de catalogo que NO se mapean a desconocido

- tipo_documento
- identificacion
- primer_apellido
- segundo_apellido
- nombres
- nombre_completo
- codigo_unidad_academica
- unidad_academica

## Campos que pueden estar vacios sin error ni advertencia

- segundo_apellido
- codigo_subunidad_academica
- subunidad_academica

## Regla especial para fechas

Para evitar ambiguedad entre formato y catalogo:

- Se acepta `DD/MM/YYYY` con separador `/`, `-` o `.`, con o sin hora (`15-05-1937`, `15/05/1937 10:30`); se
  normaliza a `DD/MM/YYYY` y se descarta la hora.
- Si la fecha tiene formato invalido (texto libre), se marca error.
- Si la fecha tiene un alias de "sin informacion" (por ejemplo, `sin informacion`, `n/a`, `no aplica`), se normaliza a `desconocido` y se marca advertencia.
- En `fecha_final_vinculacion`, `Sin fecha fin`, `Sin fecha`, `N/A`, `NA`, `-`, `Vigente` y `Actual` significan
  vinculacion abierta: se cargan vacios, sin error ni advertencia (tienen prioridad sobre la regla anterior).
- `30/12/1899` y `31/12/1899` (el dia cero de Excel, con o sin hora) se cargan vacios con advertencia ("fecha
  equivalente a vacio en Excel").
- Son error: fechas imposibles (`31/02/2020`), años anteriores a 1900, nacimiento posterior a hoy y
  `fecha_final_vinculacion` anterior a `fecha_inicial_vinculacion`.
- `MM/DD/YYYY` no ambiguo (mes > 12 y dia <= 12) es error con el mensaje "parece MM/DD/YYYY, use DD/MM/YYYY". Nunca se
  convierte automaticamente.

## Regla para catalogos (`categoria_laboral`, `nivel_academico`, `jornada_laboral`, etc.)

Antes de buscar en el catalogo se ignoran:

- Marcas de genero: `Profesor(a)`, `Asociado(a)`, `Profesora`, `Doctora`...
- Detalle despues del valor: dependencia (`Profesor Titular - Depto. X`) o campo (`Maestria en Educacion`).

Lo que aun no esta en el catalogo se normaliza a `desconocido`; el valor original queda en el archivo `ORIGINAL_`
guardado junto al normalizado y en el resumen de normalizaciones del PDF.

## Regla para el resumen de normalizaciones (PDF)

El resumen de normalizaciones aplicadas debe incluir solo cambios semanticos.

No incluir cambios cosmeticos, por ejemplo:

- Solo mayusculas/minusculas
- Solo tildes
- Solo espacios o variaciones equivalentes

Si incluir cambios de negocio, por ejemplo:

- `M` -> `hombre`
- `valor no catalogado` -> `desconocido`

## Practica recomendada en el repositorio

- Ubicar reglas funcionales en `docs/business-rules/`.
- Mantener una tabla o lista por campo para evitar contradicciones entre validadores y normalizador.
- Actualizar este documento junto con cualquier cambio en validaciones o catalogos.

## Historial

- 2026-05-29: Primera version formal del documento para Staff.
- 2026-09-30: Actualización campos `nombre_completo`, `subunidad_academica`, `codigo_unidad_academica`
- 2026-11-09: `orcid`, `cvlac` y `scholar` opcionales; nombres con puntos y comas; unidades con parentesis y signos
  habituales; fechas flexibles; nuevas equivalencias de tipo de documento; catalogos tolerantes a genero y sufijos.
- 2026-11-11: Nuevo tipo de documento `documento extranjero` (`DE`, `D.E.`, `D.E`, que antes iban a cedula de
  extranjeria) con identificacion alfanumerica de hasta 17 caracteres; `PA` → pasaporte; categorias laborales
  `decano`, `director`, `jefe` y `administrativo`, sin variantes por ahora. Correccion: una columna aceptada con un
  encabezado sin tildes o con caracteres invisibles (`Categoria Laboral`, `Nombre Completo` copiado de otra fuente) se
  validaba pero no se normalizaba ni se guardaba; ahora se renombra a su nombre canonico antes de todo el proceso.
