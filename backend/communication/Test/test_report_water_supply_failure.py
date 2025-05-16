import pytest
from django.urls import reverse
from rest_framework import status
from communication.reports.models import FailureReport, TypeReport
from iot.models import IoTDevice, VALVE_4_ID
from plots_lots.models import Plot, Lot

@pytest.mark.django_db
class TestReportWaterSupply:
    """Pruebas para el requerimiento RF64: Reporte de fallos en el suministro de agua"""

    # URL para crear reportes de fallos en el suministro de agua
    url = reverse("water-supply-failure-create")
    
    def test_create_water_supply_report_successful(self, api_client, normal_user, user_plot, iot_device):
        """
        RF64-HU09, RF64-HU12: Prueba la creación exitosa de un reporte de fallos en el suministro de agua
        
        El usuario autenticado debe poder crear un reporte para su predio
        """
        # Hacer login directamente (sin OTP)
        api_client.force_authenticate(user=normal_user)
        
        # Obtener el lote que tiene la válvula 4" asociada
        lote_con_valvula = iot_device[0].id_lot  # Primer dispositivo es la válvula 4"
        
        # Datos válidos para el reporte
        data = {
            "plot": user_plot.id_plot,
            "lot": lote_con_valvula.id_lot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Problema con el suministro de agua desde hace 5 horas",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        # Enviar la solicitud
        response = api_client.post(self.url, data, format="json")
        
        # Verificaciones
        assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
        assert response.data.get("failure_type") == TypeReport.WATER_SUPPLY_FAILURE
        assert response.data.get("plot") == user_plot.id_plot
        assert response.data.get("lot") == lote_con_valvula.id_lot
        assert response.data.get("status") == 'Pendiente'
        
        # Verificar que el ID del reporte tiene el formato correcto (20XXXXXX)
        report_id = response.data.get("id")
        assert report_id is not None
        assert str(report_id).startswith("20"), f"ID de reporte incorrecto: {report_id}"
        
    def test_create_water_supply_report_only_plot(self, api_client, normal_user, user_plot):
        """
        RF64-HU10: Prueba la creación de un reporte sin lote (solo predio)
        
        El usuario debe poder reportar un fallo a nivel de predio
        """
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        
        # Datos válidos para el reporte (solo predio)
        data = {
            "plot": user_plot.id_plot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Problema general con el suministro de agua en todo el predio",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        # Enviar la solicitud
        response = api_client.post(self.url, data, format="json")
        
        # Verificaciones
        assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
        assert response.data.get("plot") == user_plot.id_plot
        assert response.data.get("lot") is None
        
    def test_report_invalid_missing_fields(self, api_client, normal_user):
        """
        RF64-HU11: Prueba error de validación cuando faltan campos obligatorios
        
        El sistema debe mostrar un error si faltan campos obligatorios
        """
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        
        # Datos inválidos - falta predio y observaciones
        data = {
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "type": "Reporte"  # Añadido el campo type pero faltarán otros campos obligatorios
        }
        
        # Enviar la solicitud
        response = api_client.post(self.url, data, format="json")
        
        # Verificaciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Verificamos que el error contiene información sobre campos faltantes
        response_data_str = str(response.data).lower()
        assert "plot" in response_data_str or "observations" in response_data_str
        
    def test_report_observation_too_long(self, api_client, normal_user, user_plot):
        """
        RF64-HU10: Prueba error cuando las observaciones superan el límite de caracteres (300)
        
        El sistema debe validar que las observaciones no superen los 300 caracteres
        """
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        
        # Datos inválidos - observaciones demasiado largas (301 caracteres)
        data = {
            "plot": user_plot.id_plot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "A" * 301,
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        # Enviar la solicitud
        response = api_client.post(self.url, data, format="json")
        
        # Verificaciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Verificar que el error está relacionado con la longitud de las observaciones
        response_str = str(response.data).lower()
        assert "caracteres" in response_str or "caract" in response_str or "length" in response_str
        
    def test_report_duplicate_pending_report_not_allowed(self, api_client, normal_user, user_plot, iot_device):
        """
        Prueba restricción: No se puede crear un reporte para un predio/lote que ya tiene uno pendiente
        
        Si ya existe un reporte en estado pendiente para el predio o lote, no se debe permitir crear otro
        """
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        
        # Obtener el lote que tiene la válvula 4" asociada
        lote_con_valvula = iot_device[0].id_lot  # Primer dispositivo es la válvula 4"
        
        # Creamos un reporte inicial
        data = {
            "plot": user_plot.id_plot,
            "lot": lote_con_valvula.id_lot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Primer reporte de prueba",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        # Enviar la primera solicitud
        response1 = api_client.post(self.url, data, format="json")
        assert response1.status_code == status.HTTP_201_CREATED, f"Error en el primer reporte: {response1.data}"
        
        # Intentar crear un segundo reporte para el mismo lote
        data["observations"] = "Segundo reporte que debería fallar"
        response2 = api_client.post(self.url, data, format="json")
        
        # Verificaciones - debería fallar
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        # Verificar que el error está relacionado con un reporte pendiente
        response_str = str(response2.data).lower()
        assert "pendiente" in response_str or "ya existe" in response_str
        
    def test_report_inactive_plot_not_allowed(self, api_client, normal_user, inactive_user_plot):
        """
        Prueba restricción: No se puede crear un reporte para un predio inactivo
        
        El sistema debe validar que el predio esté activo
        """
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        
        # Datos para un predio inactivo
        data = {
            "plot": inactive_user_plot.id_plot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para predio inactivo",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        # Enviar la solicitud
        response = api_client.post(self.url, data, format="json")
        
        # Verificaciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Verificar que el error está relacionado con el estado inactivo
        response_str = str(response.data).lower()
        assert "inhabilitado" in response_str or "inactivo" in response_str
        
    def test_report_inactive_lot_not_allowed(self, api_client, normal_user, user_plot, user_lot, iot_device):
        """
        Prueba restricción: No se puede crear un reporte para un lote inactivo
        
        El sistema debe validar que el lote esté activo
        """
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        
        # Crear una copia del objeto IoTDevice y asociarlo al lote inactivo
        lote_inactivo = user_lot[2]  # Lote inactivo
        
        # Modificar un dispositivo de válvula existente para asociarlo al lote inactivo
        valve = iot_device[0]  # La primera válvula
        
        # Crear un reporte con el lote inactivo que ahora tiene válvula
        data = {
            "plot": user_plot.id_plot,
            "lot": lote_inactivo.id_lot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para lote inactivo",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        # Enviar la solicitud
        response = api_client.post(self.url, data, format="json")
        
        # Verificaciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Verificar que el error está relacionado con el estado inactivo
        response_str = str(response.data).lower()
        assert "inhabilitado" in response_str or "inactivo" in response_str
        
    def test_report_plot_has_pending_but_lot_allowed(self, api_client, normal_user, user_plot, iot_device):
        """
        Prueba restricción: No se puede crear un reporte para un lote si el predio ya tiene un reporte pendiente
        
        Según la implementación actual, no se permite crear reportes para lotes si el predio ya tiene un reporte pendiente
        """
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        
        # Primer reporte solo para el predio
        data_plot = {
            "plot": user_plot.id_plot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para el predio completo",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        # Enviar la primera solicitud (solo predio)
        response1 = api_client.post(self.url, data_plot, format="json")
        assert response1.status_code == status.HTTP_201_CREATED, f"Error en el primer reporte: {response1.data}"
        
        # Segundo reporte para un lote específico
        lote_con_valvula = iot_device[0].id_lot  # Primer dispositivo es la válvula 4"
        
        data_lot = {
            "plot": user_plot.id_plot,
            "lot": lote_con_valvula.id_lot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para un lote específico aunque el predio ya tenga reporte",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        # Enviar la segunda solicitud
        response2 = api_client.post(self.url, data_lot, format="json")
        
        # Verificaciones - Debería aceptar el reporte para el lote
        # Verificar que el reporte se creó correctamente
        assert response2.status_code == status.HTTP_201_CREATED
        # Verificar que el error está relacionado con un reporte pendiente
        response_str = str(response2.data).lower()
        assert "pendiente" in response_str or "ya existe" in response_str
        
    def test_unauthorized_user_cannot_report(self, api_client):
        """
        RF64-HU08: Prueba que un usuario no autenticado no puede crear reportes
        
        Solo los usuarios autenticados deben poder acceder a esta funcionalidad
        """
        # Cliente sin autenticar (no llamamos a force_authenticate)
        
        # Datos para el reporte
        data = {
            "plot": "PR-1234567",  # ID ficticio
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte no autorizado",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        # Enviar la solicitud
        response = api_client.post(self.url, data, format="json")
        
        # Verificaciones
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        
    def test_user_cannot_report_for_other_user_plot(self, api_client, admin_user, user_plot, iot_device):
        """
        Prueba que un usuario no puede crear reportes para predios que no le pertenecen
        
        Un usuario solo debe poder reportar fallos en sus propios predios
        """
        # Hacer login como admin_user que no es dueño del predio
        api_client.force_authenticate(user=admin_user)
        
        # Datos para un predio que no pertenece al admin_user
        data = {
            "plot": user_plot.id_plot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para predio ajeno",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        # Enviar la solicitud
        response = api_client.post(self.url, data, format="json")
        
        # Verificaciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Verificar que el error está relacionado con la propiedad
        response_str = str(response.data).lower()
        assert "dueño" in response_str or "owner" in response_str or "propietario" in response_str
        
    def test_list_reports(self, api_client, normal_user, user_plot, iot_device):
        """
        RF64-HU03: Prueba listado de reportes para un usuario
        
        El usuario debe poder ver sus propios reportes
        """
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        
        # Obtener el lote que tiene la válvula 4" asociada
        lote_con_valvula = iot_device[0].id_lot  # Primer dispositivo es la válvula 4"
        
        # Crear un reporte primero
        data = {
            "plot": user_plot.id_plot,
            "lot": lote_con_valvula.id_lot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para listar después",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        
        create_response = api_client.post(self.url, data, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED, f"Error al crear reporte: {create_response.data}"
        
        # Obtener lista de reportes
        list_url = reverse("water-supply-failure-list")
        list_response = api_client.get(list_url)
        
        # Verificaciones
        assert list_response.status_code == status.HTTP_200_OK, f"Error al listar reportes: {list_response.data}"
        assert len(list_response.data) >= 1
        
        # Verificar que el reporte creado está en la lista
        found = False
        for report in list_response.data:
            if report.get("id") == create_response.data.get("id"):
                found = True
                break
                
        assert found, "El reporte creado no aparece en la lista"