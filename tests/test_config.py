from app import create_app


def test_create_app_returns_flask_app_with_testing_flag():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    assert app is not None
    assert app.config["TESTING"] is True
