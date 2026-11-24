from typing import Any
from quyca.clients import gmail
from quyca.files.email_templates.staff_report_templates import build_email_template
from quyca.files.email_templates.scienti_upload_templates import build_scienti_received_templete
from quyca.models.staff_report_model import StaffReport


def send_report(
    staff_report: StaffReport,
    institution: str,
    filename: str,
    upload_date: str,
    user: str,
    email: str,
    file_type: str,
    attachments: list[dict],
    ror_id: str,
) -> dict[str, Any]:
    """Sends the validation report email with attachments."""
    tipo_correo = (
        "rechazado"
        if staff_report.total_errors > 0
        else ("advertencias" if len(staff_report.warnings) > 0 else "aceptado")
    )

    subject, body_html = build_email_template(
        status_type=tipo_correo, role=user, institution=institution, filename=filename, upload_date=upload_date
    )

    result: dict[str, Any] = gmail.send_labeled_email(
        to_email=email,
        subject=subject,
        body_html=body_html,
        attachments=attachments,
        institution=institution,
        tipo=file_type,
        ror_id=ror_id,
    )

    return result


def send_custom_email(
    subject: str, role: str, institution: str, email: str, password: str, ror_id: str
) -> dict[str, Any]:
    """Sends a custom email for user account creation."""
    body_html = f"""
            <html>
                <body style='font-family: Arial, sans-serif; line-height: 1.6;'>
                    <p>Estimado(a) <b>{role}</b> – {institution},</p>
                    <p>Nos complace informarte que tu cuenta ha sido creada exitosamente en <b><span style="color:#39658c;">Impact</span><span style="color:#f6a611;">U</span></b></p>
                    <p>Podrás acceder al módulo de <b>carga de datos institucionales</b> a través del siguiente enlace:</p>
                    <p><a href=https://impactu.colav.co/submit>https://impactu.colav.co/submit</p>
                    <p><b>Datos de acceso:</b></p>
                    <ul>
                        <li><p>Usuario: {email}</p></li>
                        <li><p>Contraseña: {password}</p></li>
                    </ul>
                    <p>Como encargado de <b>suministrar y garantizar la calidad de los datos institucionales</b>, te\n
                    invitamos a consultar la siguiente guía antes de realizar tu primera carga:\n</p>
                    <p><a href=https://data.colav.co/Formato_datos_impactu.pdf>https://data.colav.co/Formato_datos_impactu.pdf</p>
                    <p>Este documento detalla los formatos requeridos y las especificaciones necesarias para\n
                    garantizar la correcta integración de los datos en la plataforma.</p>
                    <p>Si tienes preguntas o necesitas soporte técnico, puedes escribirnos a\n
                    <strong>grupo.colav@udea.edu.co</strong></p>
                    <p>Gracias por tu compromiso con la calidad de los datos y por contribuir al fortalecimiento del\n
                    ecosistema de información científica de <b><span style="color:#39658c;">Impact</span><span style="color:#f6a611;">U</span></b></p>
                    <p>Atentamente,</p>
                    <p><b>Equipo <span style="color:#39658c;">Impact</span><span style="color:#f6a611;">U</span></b></p>
                    <br><br>
                    <em>Este es un mensaje automático. No responda a este correo.</em>
                </body>
            </html>
            """

    result: dict[str, Any] = gmail.send_labeled_email(
        to_email=email,
        subject=subject,
        body_html=body_html,
        attachments=[],
        institution=institution,
        tipo="Usuarios",
        ror_id=ror_id,
    )

    return result


def send_email_change_password(
    email: str, subject: str, password: str, institution: str, ror_id: str
) -> dict[str, Any]:
    """Sends the password reset notification email."""
    body_html = f"""
        <html>
            <body>
                <p><b><span style="color:#39658c;">Impact</span><span style="color:#f6a611;">U</span></b> te informa que tu contraseña ha sido restablecida por el administrador.</p>
                <p>Nueva contraseña: {password}</P>
                <p>Si tienes preguntas o necesitas soporte técnico, puedes escribirnos a\n
                <strong>grupo.colav@udea.edu.co</strong></p>
                <p>Atentamente,</p>
                <p><b>Equipo <span style="color:#39658c;">Impact</span><span style="color:#f6a611;">U</span></b></p>
                <br><br>
                <em>Este es un mensaje automático. No responda a este correo.</em>
            </body>
        </html>
        """

    result: dict[str, Any] = gmail.send_labeled_email(
        to_email=email,
        subject=subject,
        body_html=body_html,
        attachments=[],
        institution=institution,
        tipo="Usuarios",
        ror_id=ror_id,
    )

    return result


def send_scienti_compressed_received(
    role: str,
    institution: str,
    filename: str,
    upload_date: str,
    email: str,
    ror_id: str,
) -> dict[str, Any]:
    """Sends a confirmation email for received SCIENTI compressed files."""
    subject, body_html = build_scienti_received_templete(
        role=role, institution=institution, filename=filename, upload_date=upload_date
    )

    result: dict[str, Any] = gmail.send_labeled_email(
        to_email=email,
        subject=subject,
        body_html=body_html,
        attachments=[],
        institution=institution,
        tipo="Scienti",
        ror_id=ror_id,
    )

    return result
