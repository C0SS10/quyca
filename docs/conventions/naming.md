# Convención de nombres

Reglas para nombrar módulos, funciones y parámetros en `quyca/`. Siguen el patrón que ya usaba la mayor parte del código, así que los nombres nuevos deben parecerse a los que ya existen.

## Módulos

- `<entidad>_<capa>.py`: `work_repository.py`, `work_service.py`, `work_parser.py`, `work_generator.py`, `work_router.py`, `staff_validator.py`, `staff_normalizer.py`.
- La variante de una entidad va como prefijo, no como sufijo: `ciarp_required_fields_validator.py`, no `required_fields_validator_ciarp.py`.
- `base_<capa>.py` (`base_repository`, `base_service`, `base_parser`, `base_validator`) guarda solo lo que comparten dos o más módulos de esa capa. Si una función la usa un único módulo, va en ese módulo.
- Cada capa importa solo de las capas de abajo: router → service → repository → generator. Los parsers no importan de los repositorios, y los routers no consultan Mongo directamente. Hoy hay una excepción: `export_parser` importa `set_title_and_language` de `base_service`.

## Funciones: el verbo dice qué hace

| Verbo | Qué hace | Ejemplos |
|---|---|---|
| `get_` | Lee y devuelve. Sin efectos secundarios. | `get_work_by_id`, `get_works_by_person`, `get_works_count_by_person` |
| `search_` | Búsqueda paginada de `/search` y su conteo. | `search_works`, `search_count_works` |
| `build_` | Construye y devuelve un objeto nuevo (pipeline, `$match`, dict) sin I/O. | `build_metadata`, `build_pipeline_params`, `build_sources_match` |
| `set_` | Modifica en sitio un pipeline o un modelo y devuelve `None`. | `set_product_filters(pipeline, query_params)`, `set_title_and_language(work)` |
| `compute_` | Ejecuta agregaciones costosas. | `compute_works_available_filters` |
| `save_` / `create_` / `update_` / `delete_` / `activate_` / `deactivate_` | Escriben en la base de datos. | `save_global_works_filters`, `create_user`, `deactivate_user` |
| `parse_` | Convierte modelos o cursores al formato de la respuesta (parsers). | `parse_works`, `parse_coauthorship_by_country_map` |
| `validate_` | Valida un parámetro y lanza `InvalidParamException`. | `validate_sort`, `validate_geo_type` |
| `validate` | Regla por fila de un validador de archivos: `validate(row, index)` devuelve la lista de errores. | `country_validator.validate` |
| `normalize_` | Normaliza un valor. | `normalize_key` |
| `plot_` / `export_` | Gráficos por tipo, despachados por nombre con `globals()`. **No renombrar sin cambiar el `plot_type` que llega en la URL.** | `plot_annual_citation_count` |
| `handle_<x>_upload` | Orquesta una carga de archivo (claims, validación, guardado). | `handle_staff_upload` |
| `get(cursor)` | Único nombre de los generators. | `work_generator.get` |

- Forma general: `<verbo>_<entidad>_by_<dueño>`. La entidad va en plural si se devuelven varias: `get_works_by_affiliation`, `get_patents_by_person`.
- El conteo siempre se llama `get_<entidades>_count_by_<dueño>`, como `get_news_count_by_person` (no `news_count_by_person`).
- El nombre incluye la entidad aunque el módulo ya la diga (`user_repository.create_user`, no `user_repository.create`), porque muchas funciones se importan sueltas: `from quyca.services.base_service import set_title_and_language`.
- Las funciones privadas empiezan con `_` y no se importan desde otro módulo: `_works_match`, `_get_news`, `_submit_file`.
- La función de una ruta se nombra por lo que devuelve: `get_person_research_news`, `get_apc_csv_by_person`, `ping`. Flask usa ese nombre como endpoint, pero el proyecto no usa `url_for`, así que renombrarla no cambia la URL.

## Parámetros

- Identificadores: `<entidad>_id` (`person_id`, `affiliation_id`, `source_id`, `geo_id`). Tipos: `affiliation_type`, `geo_type`; nunca abreviados (`aff_type`).
- `query_params: QueryParams`, `pipeline_params: dict | None` (lo que la vista proyecta) y `current_url: str` se llaman siempre así.
- En pipelines:
  - `pipeline` es la lista que la función modifica;
  - `match_stages` son las etapas `$match` iniciales, a las que luego se agregan orden, proyección y paginación;
  - `match` es el dict que va dentro de `{"$match": match}`.
- Orden de los parámetros: primero lo que se modifica, después los datos y al final las opciones. Por ejemplo, `set_sort(pipeline, sort, collection)` y `set_product_filters(pipeline, query_params)`.
- Modelos por su nombre (`work`, `person`, `affiliation`). Para listas mixtas de `Work | Patent | Project` se usa `workable` / `workables`.
- Nada de `doc`, `d`, `s` o `val`; usa `document`, `item`, `header` o `value`. `df` se acepta para un `DataFrame` porque es la convención de pandas.
- Las constantes de módulo van en MAYÚSCULAS: `FILTER_STAGES`, `APC_COLUMNS`, `IDENTITY_DOCUMENT_SOURCES`.
