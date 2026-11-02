# Guía de pruebas

Cómo están organizadas las pruebas de Quyca, qué las hace seguras y cómo escribir una nueva.

## Las dos suites

| | `tests/unit` | `tests/feature` |
|---|---|---|
| Qué prueba | Reglas de negocio y flujos HTTP completos | La API contra los datos reales de desarrollo |
| Mongo | `mongomock`, en memoria y vacío en cada prueba | La base real de dev, **solo lectura** |
| Red | Bloqueada | Mongo y Elasticsearch de dev |
| Corre en el CI | Sí | No, porque allá no hay base de datos |
| Tiempo aproximado | 20 segundos | 3 minutos |

Las dos no pueden correr en el mismo proceso, porque cada una necesita una configuración distinta. Si se mezclan (por ejemplo, `pytest tests`), pytest se detiene con un mensaje claro y código de salida 4. `pytest` a secas corre solo `tests/unit`.

## Comandos

```bash
make tests-unit-dev     # solo las unitarias
make tests-feature-dev  # solo las de integración
make tests-dev          # las dos, por separado
make coverage-dev       # las dos, con el reporte de cobertura combinado
```

Las dependencias de prueba están en la imagen de Docker. Después de integrar un cambio en `pyproject.toml`, hay que reconstruirla con `make up-dev`.

## El arnés de seguridad

Una prueba no puede dañar datos ni enviar nada, aunque esté mal escrita. Las protecciones están en los `conftest.py` de cada suite.

### En `tests/unit` (`tests/unit/conftest.py`)

1. **Configuración falsa.** Antes de importar `quyca`, se sobrescriben las variables de entorno y no se lee `.env.dev`. Los servidores apuntan a `unit-tests.invalid`, un dominio que por norma nunca existe.
2. **Red bloqueada en todo el proceso.** `socket.connect`, `create_connection` y `getaddrinfo` lanzan `NetworkBlockedError`.
3. **Sin credenciales de Google.** `GOOGLE_CREDENTIALS` apunta a un archivo que no existe.
4. **Dobles explícitos.** Los fixtures `users` y `outbox` reemplazan a Mongo y a Gmail.

### En `tests/feature` (`tests/feature/conftest.py`)

1. **Escrituras prohibidas.** Todos los métodos de escritura de `pymongo` y los `aggregate` con `$out` o `$merge` lanzan `ReadOnlyViolationError`. Si una prueba necesita una escritura, debe simularla con `patch`.
2. **Sin Google ni Sentry.** Sin credenciales no se puede enviar correo ni subir a Drive, y los errores de prueba no llegan a Sentry.
3. **Archivos fuera del proyecto.** `LOCAL_STORAGE_PATH` apunta a `/tmp/quyca-feature-tests`.

Estas pruebas leen los datos de dev, así que su resultado depende de ellos. Los métodos de escritura de Elasticsearch no están bloqueados porque `quyca` no tiene ninguno: al agregar uno, hay que bloquearlo aquí.

## Fixtures de `tests/unit`

| Fixture | Para qué sirve |
|---|---|
| `users` | Colección `users` en memoria, conectada al repositorio real |
| `seed_user(email, password, **campos)` | Guarda un usuario con su hash real y devuelve el documento |
| `outbox` | Captura los correos. `outbox.last_password` da la contraseña enviada; `outbox.response` y `outbox.error` simulan fallos de Gmail |
| `app`, `client` | La aplicación real con la configuración de producción: cookies seguras y CSRF activo |
| `frozen_time` | Fija el reloj de `user_service` para probar límites de expiración |
| `fast_bcrypt` (automático) | Baja el costo de bcrypt para que las pruebas sean rápidas. `@pytest.mark.real_bcrypt` usa el de producción |

## Cómo escribir una prueba

- **Verifica el resultado, no solo el código HTTP.** Revisa lo que quedó guardado, lo que se envió y que nada cambió cuando la operación se rechaza.
- **Usa las piezas reales.** Solo se reemplaza lo que sale del proceso (Mongo, Gmail, Drive). Simular el servicio dentro de la prueba del router deja la lógica sin ejecutar: por eso `user_service` tenía 14 % de cobertura.
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

La meta del proyecto es 80-85 % con las dos suites combinadas. El CI solo corre `tests/unit` y exige un mínimo con `--cov-fail-under` en `.github/workflows/pipeline.yml`: súbelo cada vez que agregues pruebas, para que la cobertura no retroceda.

La cobertura dice qué se ejecutó, no qué se verificó. Para medir la calidad de una tanda de pruebas, introduce errores a propósito en una copia desechable del código y comprueba que las pruebas fallan.

## Reglas de negocio que protegen las pruebas de usuarios

- **El correo se envía antes de guardar.** Si Gmail falla, no queda nada escrito y se puede reintentar: un error devuelto por Gmail responde 502 y una excepción responde 500.
- **Las credenciales se generan con `secrets`**, nunca con `random`.
- **Un token válido no basta.** Cada ruta protegida y `/me` consultan si la cuenta sigue activa, así que desactivar un usuario le quita el acceso de inmediato.
- **Nadie se convierte en administrador por la API**, ni escribiendo el rol con mayúsculas o espacios.
