import io
import html as html_lib
from xhtml2pdf import pisa
from datetime import datetime
from typing import List, Dict, Any
from zoneinfo import ZoneInfo


def generate_quality_report(
    errors: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
    duplicados: List[Dict[str, Any]] | None,
    institution: str,
    filename: str,
    upload_date: str,
    user: str,
    normalized_changes: List[Dict[str, Any]] | None = None,
    has_nombre_completo: bool = False,
) -> io.BytesIO:
    """Generates the Staff PDF report with errors/warnings/duplicates."""
    report_date = datetime.now(ZoneInfo("America/Bogota")).strftime("%d/%m/%Y %H:%M")

    name_rows = ""

    if has_nombre_completo:
        name_rows = """
                <tr>
                    <td>nombre_completo</td>
                    <td>Nombre completo del autor</td>
                </tr>
            """
    else:
        name_rows = """
                <tr>
                    <td>primer_apellido</td>
                    <td>Primer apellido del autor</td>
                </tr>
                <tr>
                    <td>segundo_apellido</td>
                    <td>Segundo apellido del autor</td>
                </tr>
                <tr>
                    <td>nombres</td>
                    <td>Todos los nombres del autor</td>
                </tr>
            """

    if errors:
        title = "Reporte de Calidad de Datos"
        intro = f"""
                <h2><li>Corrección de errores en la información cargada</li></h2>
                <p>
                    Este reporte tiene como objetivo concientizar sobre la importancia de la calidad de los datos.
                    Al revisar los archivos enviados se identificaron <b>dos tipos de observaciones</b>:
                </p>
                <ul>
                    <li><b>Errores:</b> Deben corregirse de manera obligatoria antes de volver a cargar la información.</li>
                    <li><b>Advertencias:</b> No requieren corrección inmediata, pero pueden afectar el funcionamiento de algunos filtros en la plataforma 
                    (por ejemplo, que cierta información no aparezca en el excel o nuevos roles en algunas columnas).</li>
                </ul>
                <p><b>Recomendación:</b> Corregir siempre ambos tipos para garantizar la mejor calidad de los datos.</p>
                <h2><li>Estructura de Datos Esperada</li></h2>
                <p>La siguiente tabla describe el formato estándar que debe seguirse al cargar los datos:</p>
                <table>
                    <tr><th>Columna</th><th>Valores admitidos / Observaciones</th></tr>
                    <tr><td>tipo_documento</td><td>cédula de ciudadanía, cédula de extranjería, pasaporte</td></tr>
                    <tr><td>identificación</td><td>Número de identificación según tipo</td></tr>
                    {name_rows}
                    <tr><td>nivel_académico</td><td>técnico, pregrado, maestría, doctorado, especialización, especialización médica</td></tr>
                    <tr><td>tipo_contrato</td><td>vinculado, ocasional, cátedra, prestación de servicios, postdoc</td></tr>
                    <tr><td>jornada_laboral</td><td>medio tiempo, tiempo completo, tiempo parcial</td></tr>
                    <tr><td>categoría_laboral</td><td>auxiliar, asociado, titular</td></tr>
                    <tr><td>sexo</td><td>hombre, mujer, intersexual (vacío si no se tiene)</td></tr>
                    <tr><td>fechas (nacimiento / inicial vinculación / final vinculación)</td><td>Formato DD/MM/YYYY (fecha corta de Excel)</td></tr>
                    <tr><td>código_unidad_académica</td><td>Código único (fijo en futuras actualizaciones)</td></tr>
                    <tr><td>unidad_académica</td><td>Nombre completo de la facultad o dependencia</td></tr>
                    <tr><td>código_subunidad_académica</td><td>Código único de subunidad (si existe)</td></tr>
                    <tr><td>subunidad_académica</td><td>Nombre del departamento o subunidad</td></tr>
                </table>

                <h2><li> Recomendaciones Adicionales</li></h2>
                <ul>
                    <li>Evitar <b>abreviaciones</b>. Ejemplo: <i>Fac Med</i> → <i>Facultad de Medicina</i> </li>
                    <li><b>unidad_académica</b> puede equivaler a facultad en algunas instituciones.</li>
                    <li><b>subunidad_académica</b> puede equivaler a departamento.</li>
                    <li>Revisar que no existan <b>caracteres extraños</b> o problemas de codificación.</li>
                    <li>Si la institución solo maneja <b>un nivel</b>, se diligencian únicamente las unidades académicas y se deja vacío el campo de subunidades.</li>
                </ul>

                <p class="note">
                    Documento de referencia: 
                    <a href="https://data.colav.co/Formato_datos_impactu.pdf">Formato original de información</a>
                </p>
            """

    else:
        title = "Reporte de Subida Exitoso"
        intro = """
                <p>
                    El archivo fue cargado correctamente, pero se detectaron observaciones que deben ser tenidas en cuenta.
                </p>
            """
    html = f"""
        <html>
            <head>
                <style>
                    @page {{
                        @frame header_frame {{
                            -pdf-frame-content: header_content;
                            top: 0px;
                            left: 0px;
                            width: 18cm;
                            height: 100px;
                        }}
                        @frame content_frame {{
                            top: 120px;
                            left: 20px;
                            right: 20px;
                            bottom: 20px;
                        }}
                    }}
                    body {{
                        font-family: Arial, sans-serif;
                        font-size: 12px;
                    }}
                    h1, h2, h3 {{
                        color: black;
                        font-weight: bold;
                        text-align: center;
                    }}
                    h2, h3 {{
                        text-align: left;
                        margin-top: 20px;
                    }}
                    p {{
                        text-align: justify;
                        margin: 10px 0;
                    }}
                    table {{
                        width: 18cm;
                        border: 1px solid #000;
                        margin-top: 20px;
                        border-collapse: collapse;
                        table-layout: fixed;
                    }}
                    table th {{
                        background-color: #f2f2f2;
                        padding: 5px;
                        font-weight: bold;
                        text-align: center;
                    }}
                    tr, td, th {{
                        page-break-inside: avoid;
                        text-align: center;
                        padding: 5px;
                    }}
                    .header-img {{
                        width: 18cm;
                        height: auto;
                        display: block;
                        margin: 0;
                        padding: 0;
                    }}
                    .note {{
                        font-size: 11px;
                        color: #555;
                        margin-top: 10px;
                    }}
                    .cell-content{{
                        display: block;
                        white-space: normal;
                        word-wrap: break-word;
                        overflow-wrap: break-word;
                        page-break-inside: auto;
                    }}
                </style>
            </head>
            <body>
                <div id="header_content" style="width:18cm">
                    <img src="https://raw.githubusercontent.com/jhonbg/fotos/main/Membrete_Header.png" class="header-img"/>
                </div>
                    <h1>{title}</h1>
                
                <p><b>Institución:</b> {institution}<br>
                <b>Archivo validado:</b> {filename}<br>
                <b>Fecha y hora de carga:</b> {upload_date}<br>
                <b>Fecha y hora de generación del reporte:</b> {report_date}<br>
                <b>Usuario responsable:</b> {user}</p>
                {intro}
        """
    if errors:
        html += """
                    <h2><li> Errores Encontrados<li></h2>
                    <table>
                        <tr>
                            <th>Columna</th>
                            <th>Detalle</th>
                            <th>Número de filas con el error</th>
                        </tr>
            """

        for err in errors:
            columna_e = err.get("columna", "")
            detalle_e = err.get("detalle", "")
            total_e = err.get("total_filas", 0)
            html += f"""
                    <tr>
                        <td> {columna_e} </td>
                        <td> {detalle_e} </td>
                        <td> {total_e} </td>
                    </tr>
                """

        html += "</table>"
    if warnings:
        html += """
                <h2><li> Advertencias Encontradas</li></h2>
                <table>
                    <tr>
                        <th>Columna</th>
                        <th>Detalle</th>
                        <th>Valor</th>
                        <th>Número de filas con la advertencias</th>
                    </tr>
            """

        for warn in warnings:
            columna_w = warn.get("columna", "")
            detalle_w = warn.get("detalle", "")
            valor_w = warn.get("valor", "")
            total_w = warn.get("total_filas", 0)
            html += f"""
                    <tr>
                        <td> {columna_w} </td>
                        <td> {detalle_w} </td>
                        <td> {valor_w} </td>
                        <td> {total_w} </td>
                    </tr>
                """
        html += "</table>"

    if duplicados and len(duplicados) > 0:
        html += f"<h2><li>Duplicados</li></h2><p>Se detectaron {len(duplicados)} registros duplicados.</p>"
        eje = duplicados[:2]
        html += "<p><b>Ejemplo de duplicados:</b></p><ul>"
        for dup in eje:
            row = dup.get("row") or {}
            if has_nombre_completo:
                name_preview = {
                    "nombre_completo": row.get("nombre_completo"),
                }
            else:
                name_preview = {
                    "primer_apellido": row.get("primer_apellido"),
                    "nombres": row.get("nombres"),
                }
            preview = {
                "identificación": row.get("identificación"),
                **name_preview,
                "jornada_laboral": row.get("jornada_laboral"),
                "....": "....",
                "unidad_académica": row.get("unidad_académica"),
            }
            html += f"<li>{preview}</li>"
        html += "</ul>"

    if normalized_changes:
        grouped_changes: dict[str, dict[str, Any]] = {}
        for change in normalized_changes:
            column = str(change.get("columna", ""))
            original_value = str(change.get("valor_original", ""))
            normalized_value = str(change.get("valor_normalizado", ""))
            key = f"{column}::{normalized_value}"

            if key not in grouped_changes:
                grouped_changes[key] = {
                    "column": column,
                    "normalized_value": normalized_value,
                    "original_values": [],
                    "row_count": 0,
                }

            if original_value and original_value not in grouped_changes[key]["original_values"]:
                grouped_changes[key]["original_values"].append(original_value)
            grouped_changes[key]["row_count"] += 1

        html += """
                <h2><li>Normalizaciones aplicadas</li></h2>
                <p>
                    El sistema normalizó algunos valores para alinearlos con los catálogos oficiales.
                    Si consideras que alguno de estos cambios no es correcto, por favor contacta al equipo de desarrollo.
                </p>
                <table>
                    <tr>
                        <th>Columna</th>
                        <th>Valores originales observados</th>
                        <th>Valor normalizado</th>
                        <th>Número de filas afectadas</th>
                    </tr>
            """

        for item in grouped_changes.values():
            originals = "<br>".join(html_lib.escape(value) for value in item["original_values"][:3])
            normalized_value = html_lib.escape(item["normalized_value"])
            column = html_lib.escape(item["column"])
            html += f"""
                    <tr>
                        <td>{column}</td>
                        <td>{originals}</td>
                        <td>{normalized_value}</td>
                        <td>{item['row_count']}</td>
                    </tr>
                """

        html += "</table>"

    html += """
        <h2><li>Uso de los filtros en la columna <i>estado_de_validación</i></li></h2>
        <p>
            En el archivo Excel adjunto, cada fila tiene un estado que indica el resultado de su validación.
            Puedes utilizar los <b>filtros del encabezado</b> de la columna <b>estado_de_validación</b> para visualizar
            los registros según su tipo de observación.
        </p>

        <table>
            <tr>
                <th>Filtro</th>
                <th>Significado</th>
                <th>Acción recomendada</th>
            </tr>
            <tr>
                <td><b>Error</b></td>
                <td>La fila contiene uno o más errores que impiden su carga en el sistema.</td>
                <td>Debe corregirse antes de volver a enviar el archivo.</td>
            </tr>
            <tr>
                <td><b>Advertencia</b></td>
                <td>La fila presenta observaciones leves o inconsistencias no críticas.</td>
                <td>Se recomienda revisar y corregir para mantener la calidad del dato.</td>
            </tr>
            <tr>
                <td><b>Duplicado</b></td>
                <td>El registro está repetido con respecto a otro del mismo archivo.</td>
                <td>Elimina duplicados antes de volver a cargar.</td>
            </tr>
            <tr>
                <td><b>Error | Advertencia</b></td>
                <td>La fila contiene tanto errores como advertencias.</td>
                <td>Debe corregirse completamente antes de la nueva carga.</td>
            </tr>
            <tr>
                <td><b>Error | Advertencia | Duplicado</b></td>
                <td>La fila presenta todos los tipos de observación.</td>
                <td>Corregir todos los aspectos para garantizar consistencia.</td>
            </tr>
            <tr>
                <td><b>(Vacías)</b></td>
                <td>Filas sin errores, advertencias ni duplicados.</td>
                <td>No requieren ninguna acción; son registros válidos.</td>
            </tr>
        </table>

        <p class="note">
            <b>Consejo:</b> usa estos filtros para revisar rápidamente las filas afectadas.  
            Al seleccionar únicamente un tipo de estado (por ejemplo “Advertencia”), podrás identificar
            los registros que necesitan revisión sin alterar los demás.
        </p>
        </body></html>
        """

    pdf_bytes = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=pdf_bytes)
    pdf_bytes.seek(0)
    return pdf_bytes


def generate_quality_report_ciarp(
    errors: List[Dict[str, Any]],
    warnings: Dict[str, Any],
    duplicados: List[Dict[str, Any]] | None,
    institution: str,
    filename: str,
    upload_date: str,
    user: str,
) -> io.BytesIO:
    """Generates the CIARP PDF report (with warnings summary)."""
    report_date = datetime.now(ZoneInfo("America/Bogota")).strftime("%d/%m/%Y %H:%M")

    if errors:
        title = "Reporte de Calidad de Datos"
        intro = """
                <h2><li>Corrección de errores en la información cargada</li></h2>
                <p>
                    Este reporte tiene como objetivo concientizar sobre la importancia de la calidad de los datos.
                    Al revisar los archivos enviados se identificaron <b>dos tipos de observaciones</b>:
                </p>
                <ul>
                    <li><b>Errores:</b> Deben corregirse de manera obligatoria antes de volver a cargar la información.</li>
                    <li><b>Advertencias:</b> No requieren corrección inmediata, pero pueden afectar el funcionamiento de algunos filtros en la plataforma 
                    (por ejemplo, que cierta información no aparezca en el excel o nuevos roles en algunas columnas).</li>
                </ul>
                <p><b>Recomendación:</b> Corregir siempre ambos tipos para garantizar la mejor calidad de los datos.</p>
                <h2><li>Estructura de Datos Esperada</li></h2>
                <p>La siguiente tabla describe el formato estándar que debe seguirse al cargar los datos:</p>
                <table>
                    <tr><th>Columna</th><th>Valores admitidos / Observaciones</th></tr>
                    <tr><td>código_unidad_académica</td><td>Código único de la unidad académica (si no tiene un
                    código asignado, se le debe asignar y nunca se debe
                    cambiar en futuras actualizaciones)</td></tr>
                    <tr><td>código_subunidad_académica</td><td>Código único de la subunidad académica si existe (si no
                    tiene un código asignado, se le debe asignar y nunca se
                    debe cambiar en futuras actualizaciones)</td></tr>
                    <tr><td>tipo_documento</td><td>Cédula de ciudadanía, cédula de extranjería, pasaporte
                    (Si hay otro tipo, informar para reorganizar el estándar
                    de este formato)</td></tr>
                    <tr><td>identificación</td><td>Del autor</td></tr>
                    <tr><td>año</td><td>Del producto</td></tr>
                    <tr><td>título</td><td>Del producto</td></tr>
                    <tr><td>idioma</td><td>Del producto en formato ISO 639-1 (dos caracteres ej:
                    "es", "en", "fr", "it")</td></tr>
                    <tr><td>revista</td><td>Del producto</td></tr>
                    <tr><td>editorial</td><td>Del producto</td></tr>
                    <tr><td>doi</td><td>Del producto</td></tr>
                    <tr><td>issn</td><td>Del artículo si es artículo</td></tr>
                    <tr><td>isbn</td><td>Del libro si es libro</td></tr>
                    <tr><td>volumen</td><td>Del producto</td></tr>
                    <tr><td>issue</td><td>Del producto</td></tr>
                    <tr><td>primera_página</td><td>Del producto</td></tr>
                    <tr><td>pais_producto</td><td>Pais donde se publico (ISO 3166-1 alfa-2)
                    (Si hay otro tipo, informar para reorganizar el estándar
                    de este formato)</td></tr>
                    <tr><td>última_página</td><td>Del producto</td></tr>
                    <tr><td>entidad_premiadora</td><td>Nombre de la entidad que dió el premio</td></tr>
                    <tr><td>ranking</td><td>Los ejemplos de los ranking están listados a
                    continuación, donde va el tipo de documento y
                    ranking.</td></tr>
                </table>

                <p class="note">
                    Documento de referencia: 
                    <a href="https://data.colav.co/Formato_datos_impactu.pdf">Formato original de información</a>
                </p>
            """

    else:
        title = "Reporte de Subida Exitoso"
        intro = """
                <p>
                    El archivo fue cargado correctamente, pero se detectaron observaciones que deben ser tenidas en cuenta.
                </p>
            """
    html = f"""
        <html>
            <head>
                <style>
                    @page {{
                        @frame header_frame {{
                            -pdf-frame-content: header_content;
                            top: 0px;
                            left: 0px;
                            width: 18cm;
                            heigth: 100px;
                        }}
                        @frame content_frame {{
                            top: 120px;
                            left: 20px;
                            right: 20px;
                            bottom: 20px;
                        }}
                    }}
                    body {{
                        font-family: Arial, sans-serif;
                        font-size: 12px;
                    }}
                    h1, h2, h3 {{
                        color: black;
                        font-weight: bold;
                        text-align: center;
                    }}
                    h2, h3 {{
                        text-align: left;
                        margin-top: 20px;
                    }}
                    p {{
                        text-align: justify;
                        margin: 10px 0;
                    }}
                    table {{
                        width: 18cm;
                        border: 1px solid #000;
                        margin-top: 20px;
                        border-collapse: collapse;
                        table-layout: fixed;
                    }}
                    table th {{
                        background-color: #f2f2f2;
                        padding: 5px;
                        font-weight: bold;
                        text-align: center;
                    }}
                    tr, td, th {{
                        page-break-inside: avoid;
                        text-align: center;
                        padding: 5px;
                    }}
                    .header-img {{
                        width: 18cm;
                        height: auto;
                        display: block;
                        margin: 0;
                        padding: 0;
                    }}
                    .note {{
                        font-size: 11px;
                        color: #555;
                        margin-top: 10px;
                    }}
                    .cell-content{{
                        display: block;
                        white-space: normal;
                        word-wrap: break-word;
                        overflow-wrap: break-word;
                        page-break-inside: auto;
                    }}
                </style>
            </head>
            <body>
                <div id="header_content" style="width:18cm">
                    <img src="https://raw.githubusercontent.com/jhonbg/fotos/main/Membrete_Header.png" class="header-img"/>
                </div>
                <h1>{title}</h1>
                
                <p><b>Institución:</b> {institution}<br>
                <b>Archivo validado:</b> {filename}<br>
                <b>Fecha y hora de carga:</b> {upload_date}<br>
                <b>Fecha y hora de generación del reporte:</b> {report_date}<br>
                <b>Usuario responsable:</b> {user}</p>
                {intro}
        """
    if errors:
        html += """
                    <h2><li> Errores Encontrados<li></h2>
                    <table>
                        <tr>
                            <th>Columna</th>
                            <th>Detalle</th> 
                            <th>Número de filas con el error</th>
                        </tr>
            """

        for err in errors:
            columna_e = err.get("columna", "")
            detalle_e = err.get("detalle", "")
            total_e = err.get("total_filas", 0)
            html += f"""
                    <tr>
                        <td> {columna_e} </td>
                        <td> {detalle_e} </td>
                        <td> {total_e} </td>
                    </tr>
                """

        html += "</table>"
    if warnings:
        total_adv = int(warnings.get("total_advertencias", 0))
        html += f"""
                <h3>Advertencias</h3>
                <p><strong>Total de advertencias:</strong> {total_adv}</p>
            """

    if duplicados and len(duplicados) > 0:
        html += f"<h2><li>Duplicados</li></h2><p>Se detectaron {len(duplicados)} registros duplicados.</p>"
        eje = duplicados[:2]
        html += "<p><b>Ejemplo de duplicados:</b></p><ul>"
        for dup in eje:
            row = dup.get("row") or {}
            preview = {
                "identificación": row.get("identificación"),
                "primer_apellido": row.get("primer_apellido"),
                "nombres": row.get("nombres"),
                "jornada_laboral": row.get("jornada_laboral"),
                "....": "....",
                "unidad_académica": row.get("unidad_académica"),
            }
            html += f"<li>{preview}</li>"
        html += "</ul>"

    html += """
        <h2><li>Uso de los filtros en la columna <i>estado_de_validación</i></li></h2>
        <p>
            En el archivo Excel adjunto, cada fila tiene un estado que indica el resultado de su validación.
            Puedes utilizar los <b>filtros del encabezado</b> de la columna <b>estado_de_validación</b> para visualizar
            los registros según su tipo de observación.
        </p>

        <table>
            <tr>
                <th>Filtro</th>
                <th>Significado</th>
                <th>Acción recomendada</th>
            </tr>
            <tr>
                <td><b>Error</b></td>
                <td>La fila contiene uno o más errores que impiden su carga en el sistema.</td>
                <td>Debe corregirse antes de volver a enviar el archivo.</td>
            </tr>
            <tr>
                <td><b>Advertencia</b></td>
                <td>La fila presenta observaciones leves o inconsistencias no críticas.</td>
                <td>Se recomienda revisar y corregir para mantener la calidad del dato.</td>
            </tr>
            <tr>
                <td><b>Duplicado</b></td>
                <td>El registro está repetido con respecto a otro del mismo archivo.</td>
                <td>Elimina duplicados antes de volver a cargar.</td>
            </tr>
            <tr>
                <td><b>Error | Advertencia</b></td>
                <td>La fila contiene tanto errores como advertencias.</td>
                <td>Debe corregirse completamente antes de la nueva carga.</td>
            </tr>
            <tr>
                <td><b>Error | Advertencia | Duplicado</b></td>
                <td>La fila presenta todos los tipos de observación.</td>
                <td>Corregir todos los aspectos para garantizar consistencia.</td>
            </tr>
            <tr>
                <td><b>(Vacías)</b></td>
                <td>Filas sin errores, advertencias ni duplicados.</td>
                <td>No requieren ninguna acción; son registros válidos.</td>
            </tr>
        </table>

        <p class="note">
            <b>Consejo:</b> usa estos filtros para revisar rápidamente las filas afectadas.  
            Al seleccionar únicamente un tipo de estado (por ejemplo “Advertencia”), podrás identificar
            los registros que necesitan revisión sin alterar los demás.
        </p>
        </body></html>
        """

    pdf_bytes = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=pdf_bytes)
    pdf_bytes.seek(0)
    return pdf_bytes
