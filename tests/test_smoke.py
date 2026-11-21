from app import create_app


def test_app_factory_serves_login_page_with_production_style_config():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    response = app.test_client().get("/login")
    assert response.status_code == 200
