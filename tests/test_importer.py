from pathlib import Path

from app import db
from app.importer import ImportResult, import_students
from app.models import Student

FIXTURE = Path(__file__).parent / "fixtures" / "students_sample.xlsx"


def test_import_creates_students_with_class_from_nearest_header(app):
    result = import_students(str(FIXTURE))

    assert result == ImportResult(created=4, updated=0, skipped=1)
    students = {s.email: s for s in Student.query.all()}
    assert len(students) == 4
    assert students["test1@example.com"].class_name == "10A"
    assert students["test2@example.com"].class_name == "10A"
    assert students["test4@example.com"].class_name == "11B"
    assert students["test5@example.com"].class_name == "11B"
    assert students["test1@example.com"].full_name == "Test Student One"


def test_emails_are_stored_lowercased(app):
    import_students(str(FIXTURE))

    assert Student.query.filter_by(email="test2@example.com").one().full_name == "Test Student Two"


def test_student_model_has_no_id_number_column(app):
    columns = {c.name for c in Student.__table__.columns}

    assert columns == {"id", "full_name", "class_name", "email"}


def test_importing_twice_does_not_duplicate_rows(app):
    import_students(str(FIXTURE))
    second = import_students(str(FIXTURE))

    assert second == ImportResult(created=0, updated=0, skipped=1)
    assert Student.query.count() == 4


def test_reimport_counts_changed_rows_as_updated(app):
    import_students(str(FIXTURE))
    student = Student.query.filter_by(email="test4@example.com").one()
    student.class_name = "9Z"
    db.session.commit()

    result = import_students(str(FIXTURE))

    assert result == ImportResult(created=0, updated=1, skipped=1)
    assert Student.query.filter_by(email="test4@example.com").one().class_name == "11B"


def test_row_without_email_is_skipped(app):
    result = import_students(str(FIXTURE))

    assert result.skipped == 1
    assert Student.query.filter_by(full_name="Test Student Three").count() == 0


def test_cli_command_prints_counts(app):
    runner = app.test_cli_runner()
    output = runner.invoke(args=["import-students", str(FIXTURE)])

    assert output.exit_code == 0
    assert "created=4 updated=0 skipped=1" in output.output
