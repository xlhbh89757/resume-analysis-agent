from src.core.config import Settings


def test_settings_accepts_libreoffice_path():
    settings = Settings(libreoffice_path=r'D:\\LibreOffice\\program\\soffice.exe')

    assert settings.libreoffice_path == r'D:\\LibreOffice\\program\\soffice.exe'
