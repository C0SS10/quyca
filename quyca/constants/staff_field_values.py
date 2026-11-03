"""
Canonical values and normalization maps for Staff data fields.

Validators import the canonical sets (e.g. DOCUMENT_TYPES).
The normalizer imports the maps (e.g. DOCUMENT_TYPE_MAP).
"""

DOCUMENT_TYPES = {
    "cédula de ciudadanía",
    "cédula de extranjería",
    "pasaporte",
}

DOCUMENT_TYPE_MAP: dict[str, str] = {
    # cédula de ciudadanía
    "cc": "cédula de ciudadanía",
    "c.c": "cédula de ciudadanía",
    "c.c.": "cédula de ciudadanía",
    "cedula de ciudadania": "cédula de ciudadanía",
    "cédula de ciudadanía": "cédula de ciudadanía",
    "cédula ciudadanía": "cédula de ciudadanía",
    "cedula ciudadania": "cédula de ciudadanía",
    # cédula de extranjería
    "ce": "cédula de extranjería",
    "c.e": "cédula de extranjería",
    "c.e.": "cédula de extranjería",
    "cedula de extranjeria": "cédula de extranjería",
    "cédula de extranjería": "cédula de extranjería",
    "cédula extranjería": "cédula de extranjería",
    "cedula extranjeria": "cédula de extranjería",
    # pasaporte
    "ps": "pasaporte",
    "pas": "pasaporte",
    "pasaporte": "pasaporte",
}

ACADEMIC_LEVELS = {
    "sin título",
    "secundaria",
    "técnico",
    "tecnológico",
    "profesional",
    "especialización",
    "especialización médico-quirúrgica",
    "maestría",
    "doctorado",
}

ACADEMIC_LEVEL_MAP: dict[str, str] = {
    # sin título
    "sin titulo": "sin título",
    "sin título": "sin título",
    "docente sin título": "sin título",
    # secundaria
    "secundaria": "secundaria",
    "bachillerato": "secundaria",
    "bachiller": "secundaria",
    # técnico
    "tecnico": "técnico",
    "técnico": "técnico",
    # tecnológico
    "tecnologico": "tecnológico",
    "tecnológico": "tecnológico",
    "tecnologo": "tecnológico",
    "tecnólogo": "tecnológico",
    # profesional
    "profesional": "profesional",
    "pregrado": "profesional",
    "universitario": "profesional",
    "universitaria": "profesional",
    "licenciatura": "profesional",
    # especialización
    "especializacion": "especialización",
    "especialización": "especialización",
    "esp": "especialización",
    # especialización médico-quirúrgica
    "especializacion medica": "especialización médico-quirúrgica",
    "especialización médica": "especialización médico-quirúrgica",
    "especializacion medico-quirurgica": "especialización médico-quirúrgica",
    "especialización médico-quirúrgica": "especialización médico-quirúrgica",
    "especializacion medico quirurgica": "especialización médico-quirúrgica",
    "especialización médico quirúrgica": "especialización médico-quirúrgica",
    "especialidad medico quirurgica": "especialización médico-quirúrgica",
    "especialidad médico quirúrgica": "especialización médico-quirúrgica",
    # maestría
    "maestria": "maestría",
    "maestría": "maestría",
    "magister": "maestría",
    "máster": "maestría",
    "master": "maestría",
    "msc": "maestría",
    "m.sc": "maestría",
    # doctorado
    "doctorado": "doctorado",
    "doctor": "doctorado",
    "phd": "doctorado",
    "ph.d": "doctorado",
    "ph.d.": "doctorado",
    "postdoc": "doctorado",
    "postdoctorado": "doctorado",
    "post-doc": "doctorado",
    "post-doctorado": "doctorado",
    "post doctorado": "doctorado",
    "posdoctorado": "doctorado",
}

CONTRACT_TYPES = {
    "término fijo",
    "término indefinido",
    "vinculado",
    "ocasional",
    "cátedra",
    "prestación de servicios",
    "postdoc",
    "ad honorem",
}

CONTRACT_TYPE_MAP: dict[str, str] = {
    # término fijo
    "termino fijo": "término fijo",
    "término fijo": "término fijo",
    "fijo": "término fijo",
    "contrato a término fijo": "término fijo",
    "cont. 101 h. catedra": "término fijo",
    "contrato 101": "término fijo",
    # término indefinido
    "termino indefinido": "término indefinido",
    "término indefinido": "término indefinido",
    "indefinido": "término indefinido",
    "contrato a término indefinido": "término indefinido",
    "docente universitario": "término indefinido",
    # vinculado
    "vinculado": "vinculado",
    "planta": "vinculado",
    # ocasional
    "ocasional": "ocasional",
    # cátedra
    "catedra": "cátedra",
    "cátedra": "cátedra",
    "hora catedra": "cátedra",
    "hora cátedra": "cátedra",
    "docente catedra": "cátedra",
    "docente cátedra": "cátedra",
    "docente de catedra": "cátedra",
    "docente de cátedra": "cátedra",
    "catedrático": "cátedra",
    "horas (profesores de catedra)": "cátedra",
    # prestación de servicios
    "prestacion de servicios": "prestación de servicios",
    "prestación de servicios": "prestación de servicios",
    "servicios": "prestación de servicios",
    # postdoc
    "postdoc": "postdoc",
    "postdoctorado": "postdoc",
    "post-doc": "postdoc",
    "post-doctorado": "postdoc",
    "post doctorado": "postdoc",
    # ad honorem
    "ad honorem": "ad honorem",
    "adhonorem": "ad honorem",
    "ad-honorem": "ad honorem",
}

WORK_SCHEDULES = {
    "medio tiempo",
    "tiempo completo",
    "tiempo parcial",
    "hora cátedra",
}

WORK_SCHEDULE_MAP: dict[str, str] = {
    # medio tiempo
    "medio tiempo": "medio tiempo",
    "mt": "medio tiempo",
    "1/2 tiempo": "medio tiempo",
    "media jornada": "medio tiempo",
    # tiempo completo
    "tiempo completo": "tiempo completo",
    "tc": "tiempo completo",
    "completo": "tiempo completo",
    "jornada completa": "tiempo completo",
    # tiempo parcial
    "tiempo parcial": "tiempo parcial",
    "tp": "tiempo parcial",
    "parcial": "tiempo parcial",
    "jornada parcial": "tiempo parcial",
    # hora cátedra
    "por horas": "hora cátedra",
    "horas": "hora cátedra",
    "hora catedra": "hora cátedra",
    "hora cátedra": "hora cátedra",
    "cátedra": "hora cátedra",
}

JOB_CATEGORIES = {
    "instructor asistente",
    "instructor asociado",
    "profesor asistente",
    "profesor auxiliar",
    "profesor asociado",
    "profesor titular",
    "profesor investigador asistente",
    "profesor investigador asociado",
    "profesor investigador titular",
    "instructor investigador asociado",
    "profesor emérito",
    "ordinario",
}

JOB_CATEGORY_MAP: dict[str, str] = {
    # instructor asistente
    "instructor asistente": "instructor asistente",
    # instructor asociado
    "instructor asociado": "instructor asociado",
    # profesor asistente
    "profesor asistente": "profesor asistente",
    "asistente": "profesor asistente",
    # profesor auxiliar
    "profesor auxiliar": "profesor auxiliar",
    "auxiliar": "profesor auxiliar",
    # profesor asociado
    "profesor asociado": "profesor asociado",
    "asociado": "profesor asociado",
    # profesor titular
    "profesor titular": "profesor titular",
    "titular": "profesor titular",
    # profesor investigador asistente
    "profesor investigador asistente": "profesor investigador asistente",
    "investigador asistente": "profesor investigador asistente",
    # profesor investigador asociado
    "profesor investigador asociado": "profesor investigador asociado",
    "investigador asociado": "profesor investigador asociado",
    # profesor investigador titular
    "profesor investigador titular": "profesor investigador titular",
    "investigador titular": "profesor investigador titular",
    # instructor investigador asociado
    "instructor investigador asociado": "instructor investigador asociado",
    "instructor asociado investigador": "instructor investigador asociado",
    # emérito
    "profesor emérito": "profesor emérito",
    "profesor emerito": "profesor emérito",
    "emerito": "profesor emérito",
    "emérito": "profesor emérito",
    # ordinario
    "ordinario": "ordinario",
}

SEX = {
    "hombre",
    "mujer",
    "intersexual",
    "no binario",
}

SEX_MAP: dict[str, str] = {
    # hombre
    "hombre": "hombre",
    "masculino": "hombre",
    "m": "hombre",
    # mujer
    "mujer": "mujer",
    "femenino": "mujer",
    "f": "mujer",
    # intersexual
    "intersexual": "intersexual",
    "i": "intersexual",
    # no binario
    "no binario": "no binario",
    "nobinario": "no binario",
    "no-binario": "no binario",
    "non binary": "no binario",
    "non-binary": "no binario",
    "nb": "no binario",
}
