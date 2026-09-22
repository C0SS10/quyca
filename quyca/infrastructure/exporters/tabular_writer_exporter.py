import csv
from io import BytesIO, StringIO
from typing import Generator
from openpyxl import Workbook


def write_csv(rows: Generator[dict, None, None], columns: list[str]) -> Generator[str, None, None]:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, escapechar="\\", quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    for row in rows:
        writer.writerow(row)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)


def write_excel(rows: Generator[dict, None, None], columns: list[str], sheet_name: str = "Data") -> BytesIO:
    output = BytesIO()
    workbook = Workbook(write_only=True)
    worksheet = workbook.create_sheet(sheet_name)
    worksheet.append(columns)

    for row in rows:
        worksheet.append([row.get(column) for column in columns])

    workbook.save(output)
    output.seek(0)
    return output
