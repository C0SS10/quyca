from typing import Tuple


def build_scienti_received_templete(role: str, institution: str, filename: str, upload_date: str) -> Tuple[str, str]:
    """Builds the email template confirming receipt of a SCIENTI file."""

    subject = f"Confirmación de recepción de datos SCIENTI - {institution} - {upload_date}"

    body_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <p>Estimado(a)  <b>{role}</b> - {institution}</p>
            <p>
                Te informamos que hemos recibido correctamente el archivo comprimido asociado al sistema <b>SCIENTI</b>:
                <b>{filename}</b>, cargado en la plataforma el día <b>{upload_date}</b>.
            </p>
            
            <p>
                Los datos contenidos en este archivos serán sometidos al proceso de validación por parte del <b>Equipo <span style="color:#39658c;">Impact</span><span style="color:#f6a611;">U</span></b>
                Una vez finalice la validación, recibirás un nuevo correo con los resultados y las acciones a seguir en caso de encontrar inconsistencias.
            </p>
            
            <p>
                Gracias por tu colaboración en el aseguramiento de la calidad de los datos.
            </p>
            
            <p>
                <b>Equipo <span style="color:#39658c;">Impact</span>
                <span style="color:#f6a611;">U</span></b>
            </p>

            <br><br>
            <em>Este es un mensaje automático. Por favor no respondas a este correo.</em>
        </body>
    </html>
    """

    return subject, body_html
