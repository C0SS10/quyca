# Guía de pruebas

Cómo están organizadas las pruebas de Quyca, qué las hace seguras y cómo escribir una nueva.

## La pirámide

Las pruebas siguen la pirámide de Mike Cohn: muchas pruebas pequeñas y rápidas abajo, pocas y completas arriba. La capa de una prueba la define **qué es real** en ella.

```
tests/
  support/        arnés aislado, fixtures y fábricas de Excel compartidas por unit e integration
  unit/           una función o un módulo, sin infraestructura
    clients/ files/ generators/ normalizers/ parsers/ repositories/ security/ services/ validators/
  integration/    varias piezas juntas con infraestructura falsa (mongomock, disco temporal, Gmail y Drive falsos)
    repositories/   repositorio + mongomock o disco
    services/       servicio + repositorio
    routes/         HTTP de punta a punta dentro de la app, con dobles para lo externo
  api/            endpoints por HTTP contra Mongo y Elasticsearch reales de dev, en solo lectura
    affiliations/ person/ work/ sources/ patent/ project/ geo/ search/
```

| | `unit` | `integration` | `api` |
|---|---|---|---|
| Qué es real | Solo el código bajo prueba | Nuestro código completo; la infraestructura es falsa | Todo: Mongo y Elasticsearch de dev |
| Mongo | Ninguno (o un `MagicMock`) | `mongomock`, vacío en cada prueba | La base de dev, **solo lectura** |
| Red | Bloqueada | Bloqueada | Mongo y Elasticsearch de dev |
| Puede correr en un CI | Sí | Sí | No |
| Tiempo aproximado | 10 segundos | 25 segundos | 2 minutos |

### ¿Dónde va mi prueba?

1. ¿Necesita datos reales de dev para tener sentido (una consulta, una agregación, una gráfica)? → `api/`, por HTTP.
2. ¿Usa varias piezas a la vez: una ruta, un servicio con su repositorio, o un repositorio con `mongomock` o con disco? → `integration/`.
3. Si no: una función o un módulo con sus colaboradores simulados → `unit/`, en la carpeta del módulo que prueba.

Las pruebas de `api` no simulan capas internas: si una prueba de ruta necesita `patch` sobre un servicio o un repositorio, es de `integration/routes`.

### Por qué hay dos ejecuciones

`unit` e `integration` corren con una configuración falsa y `api` con la real, y el cliente de Mongo se crea al importar `quyca`. Por eso no pueden compartir un proceso: `pytest` a secas corre `unit` e `integration`, y `api` se corre aparte con `pytest tests/api`. Si se mezclan (por ejemplo, `pytest tests`), pytest se detiene antes de correr nada, con un mensaje que explica cómo correrlas.

## Comandos

```bash
make tests-unit-dev         # unit
make tests-integration-dev  # integration
make tests-api-dev          # api, contra la base de dev
make tests-dev              # las tres
make coverage-dev           # las tres, con el reporte de cobertura combinado
```

Las dependencias de prueba están en la imagen de Docker. Después de integrar un cambio en `pyproject.toml`, hay que reconstruirla con `make up-dev`.

## El arnés de seguridad

Una prueba no puede dañar datos ni enviar nada, aunque esté mal escrita.

### En `unit` e `integration` (`tests/support/isolated.py`)

Los `conftest.py` de las dos carpetas cargan este módulo.

1. **Configuración falsa.** Antes de importar `quyca`, se sobrescriben las variables de entorno y no se lee `.env.dev`. Los servidores apuntan a `unit-tests.invalid`, un dominio que por norma nunca existe.
2. **Red bloqueada en todo el proceso.** `socket.connect`, `create_connection` y `getaddrinfo` lanzan `NetworkBlockedError`.
3. **Sin credenciales de Google.** `GOOGLE_CREDENTIALS` apunta a un archivo que no existe.
4. **Dobles explícitos.** Los fixtures `users` y `outbox` reemplazan a Mongo y a Gmail.

### En `api` (`tests/api/conftest.py`)

1. **Escrituras prohibidas.** Todos los métodos de escritura de `pymongo` y los `aggregate` con `$out` o `$merge` lanzan `ReadOnlyViolationError`.
2. **Sin Google ni Sentry.** Sin credenciales no se puede enviar correo ni subir a Drive, y los errores de prueba no llegan a Sentry.
3. **Archivos fuera del proyecto.** `LOCAL_STORAGE_PATH` apunta a `/tmp/quyca-api-tests`.

Estas pruebas leen los datos de dev, así que su resultado depende de ellos. Los métodos de escritura de Elasticsearch no están bloqueados porque `quyca` no tiene ninguno: al agregar uno, hay que bloquearlo aquí.

## Fixtures de `unit` e `integration` (`tests/support/isolated.py`)

| Fixture | Para qué sirve |
|---|---|
| `users` | Colección `users` en memoria, conectada al repositorio real |
| `seed_user(email, password, **campos)` | Guarda un usuario con su hash real y devuelve el documento |
| `outbox` | Captura los correos. `outbox.last_password` da la contraseña enviada; `outbox.response` y `outbox.error` simulan fallos de Gmail |
| `app`, `client` | La aplicación real con la configuración de producción: cookies seguras y CSRF activo. Lo que guarda en disco (`LOCAL_STORAGE_PATH`) cae en la carpeta temporal de la prueba |
| `as_user`, `as_admin` | Cliente con la sesión iniciada de un usuario de institución o de un administrador |
| `sign_in(client, email, password)`, `csrf_headers(client)` | Inician sesión y dan el encabezado CSRF que exigen las peticiones que modifican algo |
| `frozen_time` | Fija el reloj de `user_service` para probar límites de expiración |
| `fast_bcrypt` (automático) | Baja el costo de bcrypt para que las pruebas sean rápidas. `@pytest.mark.real_bcrypt` usa el de producción |

### Archivos de Excel para pruebas

`tests/support/project_files.py` construye archivos en memoria:

- `make_xlsx(filas)`: un `.xlsx` con openpyxl. `VALID_PROJECT` es una fila válida del formato de proyectos.
- `make_excel_style_xlsx(filas)`: un `.xlsx` con los textos en `xl/sharedStrings.xml`, **como los guarda Excel**. openpyxl guarda los textos dentro de la hoja, así que sin esta función esa parte del lector nunca se probaría.
- `rewrite_member(xlsx, archivo_interno, cambio)`: daña o altera un archivo interno del `.xlsx` para probar archivos corruptos o maliciosos.

## Cómo escribir una prueba

- **Verifica el resultado, no solo el código HTTP.** Revisa lo que quedó guardado, lo que se envió y que nada cambió cuando la operación se rechaza.
- **Usa las piezas reales.** Solo se reemplaza lo que sale del proceso (Mongo, Gmail, Drive). Para Gmail y Drive se simula el servicio de Google (`MagicMock`), no nuestras funciones, así se prueba la lógica de carpetas, etiquetas y errores. Simular el servicio dentro de la prueba del router deja la lógica sin ejecutar: por eso `user_service` tenía 14 % de cobertura.
- **Prueba los límites.** Vacío, `None`, tipo incorrecto, exactamente en el límite y un segundo antes.
- **Prueba los permisos ruta por ruta.** Sin sesión, con otro rol y sin token CSRF.
- **Escribe en inglés el nombre de la prueba y en español los comentarios y los `id` de los casos.**

Ejemplo:

```python
@pytest.mark.parametrize(
    "new_role",
    [pytest.param("admin", id="minusculas"), pytest.param(" ADMIN ", id="con-espacios")],
)
def test_cannot_promote_to_admin(seed_user: SeedUser, users: mongomock.Collection, new_role: str) -> None:
    seed_user()

    with pytest.raises(ForbiddenException, match="admin"):
        user_service.update_user_info(USER_EMAIL, USER_EMAIL, new_role, {"role": new_role})

    assert users.find_one({"email": USER_EMAIL})["role"] == "staff"
```

### Qué usamos de pytest

- `parametrize` con `pytest.param(..., id=...)`: cada caso tiene un nombre legible en el reporte.
- Fábricas como fixtures (`seed_user`) y `monkeypatch`, que se revierte solo al terminar la prueba.
- `pytest.raises(..., match=...)`: verifica también el mensaje, no solo el tipo.
- `subtests`: revisa cada elemento de una lista sin detenerse en el primer fallo.
- `caplog`: verifica lo que se registró en el log.
- Marcadores estrictos (`--strict-markers`) y `xfail_strict`.

### Bugs pendientes: `xfail`

Si una prueba descubre un bug que no se va a corregir en ese momento, se deja escrita con el comportamiento **correcto** y se marca así:

```python
@pytest.mark.xfail(reason="BUG-09: descripción corta del problema.", raises=AssertionError)
```

`raises=AssertionError` hace que cualquier otro error siga contando como fallo. Como `xfail_strict` está activo, al corregir el bug la prueba falla con `XPASS`, y eso obliga a quitar la marca. Para revisar el motivo real de cada una, usa `pytest --runxfail`.

## Límites de `mongomock`

`mongomock` no es Mongo. Si un comportamiento depende de cómo responde el servidor, compruébalo una vez contra un Mongo real y desechable, de la misma versión que usa el servidor:

```bash
docker run -d --rm --name mongo-check --network none mongo:8.2
docker run --rm --network container:mongo-check colav/quyca-dev:dev python -c "..."
docker stop mongo-check
```

Diferencia conocida: `{"$set": {"apikey.expires": 1}}` sobre `apikey: null` funciona en `mongomock`, pero Mongo 8.2 responde `WriteError 28`.

## Cobertura

La meta del proyecto es 80-85 % con las tres capas combinadas (`make coverage-dev`). Si el CI vuelve a correr las pruebas, conviene que ejecute `pytest --cov --cov-fail-under=<mínimo actual>` para que la cobertura no retroceda.

La cobertura dice qué se ejecutó, no qué se verificó. Para medir la calidad de una tanda de pruebas, introduce errores a propósito en una copia desechable del código y comprueba que las pruebas fallan.

## Reglas de negocio que protegen las pruebas de usuarios

- **El correo se envía antes de guardar.** Si Gmail falla, no queda nada escrito y se puede reintentar: un error devuelto por Gmail responde 502 y una excepción responde 500.
- **Las credenciales se generan con `secrets`**, nunca con `random`.
- **Un token válido no basta.** Cada ruta protegida y `/me` consultan si la cuenta sigue activa, así que desactivar un usuario le quita el acceso de inmediato.
- **Nadie se convierte en administrador por la API**, ni escribiendo el rol con mayúsculas o espacios.

## Reglas de negocio que protegen las pruebas de cargas

- **Ninguna carga acepta un archivo vacío** (proyectos, CIARP, Scienti y staff): no se guarda ni se envía correo.
- **Las marcas del Excel de validación caen en la fila correcta**, aunque el archivo tenga filas en blanco en medio (CIARP y staff).
- **Los colores del Excel de validación no cambian los datos.** Se aplican con formato condicional, así que las fechas siguen siendo fechas y los colores acompañan a la fila si el usuario la ordena.
- **Scienti confirma la recepción solo después de guardar el archivo.** Si el guardado falla, no se envía el correo de "recibido".
- **El texto que viene del archivo o de la sesión se muestra en el PDF como texto**, nunca se interpreta como HTML.
- **Un apóstrofe en el nombre de la institución no rompe la búsqueda de carpetas en Drive**, y un `ror_id` con `/` no rompe el guardado local.
