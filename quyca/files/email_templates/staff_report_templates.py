"""
Email templates for validation outcomes (rejected / warnings / accepted).
"""


def build_email_template(
    status_type: str, role: str, institution: str, filename: str, upload_date: str
) -> tuple[str, str]:
    """Builds the validation result email template based on status."""
    subject = f"Reporte de Validación de Datos {status_type.upper()} - {institution} - {upload_date}"

    if status_type == "rechazado":
        body_html = f"""<p>Estimado(a) <b>{role}</b> - {institution},</p>
        <p>Hemos recibido el archivo <b>{filename}</b> cargado en la plataforma el día <b>{upload_date}</b>.</p>
        <p>Durante la validación, se identificaron <b>errores</b> que impiden continuar con el proceso de integración a la plataforma.</b>
        <p><u>Adjunto encontrarás:</u></p>
        <ul>
            <li>El <b>Reporte de Calidad de Datos (PDF)</b>, donde se detallan los errores y advertencias detectados.</li>
            <li>El <b>archivo original en Excel</b>, al cual se le han agregado dos columnas al final:
                <ul>
                    <li><b>Estado de validación</b>: indica si la fila es Válida en vacío, presenta “Error”, presenta “Advertencia” o presenta Duplicados.</li>
                    <li><b>Observaciones</b>: describe el hallazgo correspondiente en cada caso.</li>
                </ul>
            </li>
        </ul>
        <p>Esto te permitirá identificar fácilmente qué filas requieren corrección.</p>
        <p><b>Importante:</b> Una vez hayas realizado los ajustes, recuerda eliminar las dos columnas adicionales antes de volver a subir el archivo a la plataforma.</p>
        <ul>
            <li><b>Errores:</b> deben corregirse obligatoriamente antes de cargar nuevamente.<br></li>
            <li><b>Advertencias:</b> no requieren corrección inmediata, pero pueden afectar el correcto funcionamiento de algunos procesos en la plataforma.</li>
        </ul>
        <p>Te invitamos a realizar las correcciones dentro del plazo establecido para la entrega de datos. En caso de no hacerlo dentro del tiempo definido, los datos deberán esperar hasta la siguiente actualización semestral.</p>
        <p>Si tienes dudas sobre cómo corregir los errores reportados, puedes consultar la guía: <i><a href=https://data.colav.co/Formato_datos_impactu.pdf>
        Formato talento humano, CIARP y Dump Minciencias CoLaV</a></i> o escribirnos a <a href="mailto:grupo.colav@udea.edu.co">grupo.colav@udea.edu.co</a>.</p>
        <p>Gracias por tu colaboración en garantizar la calidad de la información.</p>
        <p>Atentamente,</p>
        <p><b>Equipo <span style="color:#39658c;">Impact</span><span style="color:#f6a611;">U</span></b></p>
        """
    elif status_type == "advertencias":
        body_html = f"""<p>Estimado(a) <b>{role}</b> - {institution},</p>
        <p>Hemos recibido el archivo <b>{filename}</b> cargado en la plataforma el día <b>{upload_date}</b>.</p>
        <p>El archivo ha sido <b>aceptado</b> y continuará con el proceso de integración de datos a la plataforma.</p>
        <p>Adjunto encontrarás el <b>Reporte de Calidad de Datos (PDF)</b>, donde se detallan las advertencias identificadas durante la validación.</p>
        <p><b>Advertencias:</b> no requieren corrección inmediata, pero pueden afectar el correcto funcionamiento de algunos procesos en la plataforma.</p>
        <ul>
            <li><p>Ten en cuenta que algunos hallazgos marcados como advertencia pueden deberse a nuevos valores en ciertos campos, los cuales serán estudiados por nuestro equipo para determinar si pueden añadirse a los estándares de validación en el futuro.</p></li>
            <li><p>Tus datos ingresarán al proceso de integración en la plataforma y se verán reflejados en la próxima actualización semestral.</p></li>
        </ul>
        <p>Si deseas, puedes realizar los ajustes correspondientes para mejorar la calidad de tu información, aunque no es obligatorio en esta etapa.</p>
        <p>Si tienes dudas sobre el reporte, puedes consultar la guía: <i><a href=https://tinyurl.com/289py4re>
        Formato talento humano, CIARP y Dump Minciencias CoLaV</a></i> o escribirnos a <a href="mailto:grupo.colav@udea.edu.co">grupo.colav@udea.edu.co</a>.</p>
        <p>Gracias por tu colaboración en garantizar la calidad de la información.</p>
        <p>Atentamente,</p>
        <p><b>Equipo <span style="color:#39658c;">Impact</span><span style="color:#f6a611;">U</span></b></p>
        """
    else:
        body_html = f"""<p>Estimado(a) <b>{role}</b> – {institution},</p>
        <p>Hemos recibido el archivo <b>{filename}</b> cargado en la plataforma el día <b>{upload_date}</b>.</p>
        <p>Nos complace informarte que el archivo <b>superó exitosamente todas las validaciones</b> y no se encontraron errores ni advertencias.</p>
        <p>Adjunto encontrarás el <b>archivo Excel normalizado</b> con las columnas de validación y observación para trazabilidad. Si hubo normalizaciones, también encontrarás un <b>PDF</b> con ejemplos de los valores ajustados.</p>
        <p>Tus datos ingresarán al proceso de integración en la plataforma y se verán reflejados en la próxima actualización semestral.</p>
        <p><b>Felicitaciones</b> por el excelente trabajo en la preparación y calidad de la información.</p>
        <p>Si tienes preguntas o requieres soporte adicional, puedes escribirnos a <a href="mailto:grupo.colav@udea.edu.co">grupo.colav@udea.edu.co</a>.</p>
        <p>Gracias por tu compromiso con la calidad de los datos y por contribuir al fortalecimiento de la plataforma.</p>
        <p><b>Equipo <span style="color:#39658c;">Impact</span><span style="color:#f6a611;">U</span></b></p>
        """

    return subject, body_html
