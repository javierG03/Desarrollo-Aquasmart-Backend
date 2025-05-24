import pytest
from django.urls import reverse
from rest_framework import status
from auditlog.models import LogEntry

@pytest.mark.django_db
def test_audit_log_list_view(api_client, admin_user, login_and_validate_otp):
    """
    Verifica que un administrador autenticado puede visualizar la lista de acciones del sistema (audit log).
    """
    # Autenticación como admin
    client = login_and_validate_otp(api_client, admin_user, "AdminPass123@")

    # Crear una acción para que haya al menos un log (puedes ajustar según tu sistema)
    # Por ejemplo: admin_user.save()

    # Obtener la URL de la vista de log (ajusta el nombre si es diferente)
    url = reverse("audit-logs")  # Asegúrate que este nombre coincide con tu urls.py

    response = client.get(url)
    print("Response status:", response.status_code)
    print("Response data:", response.data)

    assert response.status_code == status.HTTP_200_OK, "No se pudo acceder al historial de acciones"
    assert isinstance(response.data, dict) or isinstance(response.data, list), "La respuesta no es una lista ni un dict paginado"
    # Si usas paginación, los resultados estarán en response.data['results']
    results = response.data.get('results', response.data)
    assert len(results) > 0, "No se encontraron acciones en el historial"
    for entry in results:
        assert "id" in entry
        assert "actor" in entry
        assert "action" in entry
        assert "content_type" in entry
        assert "created" in entry
    print("✅ Visualización de acciones del sistema verificada correctamente.")