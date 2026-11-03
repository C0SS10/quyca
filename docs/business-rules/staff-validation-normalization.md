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

- Si la fecha tiene formato invalido, se marca error.
- Si la fecha tiene un alias de "sin informacion" (por ejemplo, `sin informacion`, `n/a`, `no aplica`), se normaliza a `desconocido` y se marca advertencia.

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
