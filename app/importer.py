import re
from dataclasses import dataclass

from openpyxl import load_workbook

from app import db
from app.models import Student

# Class codes such as "10A" or "11Б": 1-2 digits followed by one letter.
_CLASS_CODE = re.compile(r"^\d{1,2}\s*[^\W\d_]$")

# Column indexes (0-based) in the school sheet, as found in the real file:
# A empty, B class code, C full name, D ID-like number (ignored), E email.
_COL_A, _COL_B, _COL_C, _COL_E = 0, 1, 2, 4


@dataclass(frozen=True)
class ImportResult:
    created: int
    updated: int
    skipped: int


def _cell_text(row, idx: int) -> str:
    if idx >= len(row) or row[idx] is None:
        return ""
    return str(row[idx]).strip()


def _class_code(row) -> str | None:
    for idx in (_COL_B, _COL_A):
        text = _cell_text(row, idx)
        if text and _CLASS_CODE.match(text):
            return text
    return None


def import_students(path: str) -> ImportResult:
    """Upsert students from the school xlsx, matching on lowercased email.

    Only class, full name and email are read. The ID-like column is ignored.
    """
    created = updated = skipped = 0
    current_class: str | None = None

    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = wb.worksheets[0]
        # Row 1 is the header row.
        for raw in sheet.iter_rows(min_row=2, values_only=True):
            row = tuple(raw)
            class_code = _class_code(row)
            full_name = _cell_text(row, _COL_C)
            email = _cell_text(row, _COL_E).lower()

            if not full_name and not email:
                # Standalone class header row (or a blank spacer row).
                if class_code is not None:
                    current_class = class_code
                continue
            # A data row carries its own class code; otherwise use the nearest header above.
            if class_code is not None:
                current_class = class_code
            if not email or current_class is None:
                skipped += 1
                continue

            student = Student.query.filter_by(email=email).first()
            if student is None:
                db.session.add(Student(full_name=full_name, class_name=current_class, email=email))
                created += 1
            elif student.full_name != full_name or student.class_name != current_class:
                student.full_name = full_name
                student.class_name = current_class
                updated += 1
    finally:
        wb.close()

    db.session.commit()
    return ImportResult(created=created, updated=updated, skipped=skipped)
