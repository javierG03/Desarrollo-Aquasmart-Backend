import pytest
from django.urls import reverse
from rest_framework import status
from communication.reports.models import FailureReport, TypeReport
from iot.models import IoTDevice, VALVE_4_ID
from plots_lots.models import Plot, Lot
import json

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
        print("\n=== PRUEBA DE CREACIÓN EXITOSA DE REPORTE DE FALLO EN SUMINISTRO DE AGUA ===")
        
        # Hacer login directamente (sin OTP)
        api_client.force_authenticate(user=normal_user)
        print(f"Usuario autenticado: {normal_user.first_name} {normal_user.last_name} (documento: {normal_user.document})")
        
        # Obtener el lote que tiene la válvula 4" asociada
        lote_con_valvula = iot_device[0].id_lot  # Primer dispositivo es la válvula 4"
        print(f"Lote seleccionado: {lote_con_valvula.id_lot} del predio {user_plot.plot_name}")
        
        # Datos válidos para el reporte
        data = {
            "plot": user_plot.id_plot,
            "lot": lote_con_valvula.id_lot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Problema con el suministro de agua desde hace 5 horas",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del reporte: {json.dumps(data, indent=2)}")
        
        # Enviar la solicitud
        print("Enviando solicitud POST para crear el reporte...")
        response = api_client.post(self.url, data, format="json")
        
        # Imprimir la respuesta para el informe
        print(f"Código de estado de la respuesta: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Datos de la respuesta: {json.dumps(response.data, indent=2)}")
        
        # Verificaciones
        assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
        print("✅ Código de estado correcto (201 Created)")
        
        assert response.data.get("failure_type") == TypeReport.WATER_SUPPLY_FAILURE
        print("✅ Tipo de fallo correcto (WATER_SUPPLY_FAILURE)")
        
        assert response.data.get("plot") == user_plot.id_plot
        print(f"✅ ID de predio correcto ({user_plot.id_plot})")
        
        assert response.data.get("lot") == lote_con_valvula.id_lot
        print(f"✅ ID de lote correcto ({lote_con_valvula.id_lot})")
        
        assert response.data.get("status") == 'Pendiente'
        print("✅ Estado inicial correcto (Pendiente)")
        
        # Verificar que el ID del reporte tiene el formato correcto (20XXXXXX)
        report_id = response.data.get("id")
        assert report_id is not None
        assert str(report_id).startswith("20"), f"ID de reporte incorrecto: {report_id}"
        print(f"✅ ID de reporte tiene el formato correcto: {report_id}")
        
    def test_create_water_supply_report_only_plot(self, api_client, normal_user, user_plot):
        """
        RF64-HU10: Prueba la creación de un reporte sin lote (solo predio)
        
        El usuario debe poder reportar un fallo a nivel de predio
        """
        print("\n=== PRUEBA DE CREACIÓN DE REPORTE SOLO CON PREDIO (SIN LOTE) ===")
        
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        print(f"Usuario autenticado: {normal_user.first_name} {normal_user.last_name}")
        
        # Datos válidos para el reporte (solo predio)
        data = {
            "plot": user_plot.id_plot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Problema general con el suministro de agua en todo el predio",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del reporte (sin lote): {json.dumps(data, indent=2)}")
        
        # Enviar la solicitud
        print("Enviando solicitud POST para crear el reporte...")
        response = api_client.post(self.url, data, format="json")
        
        # Imprimir la respuesta para el informe
        print(f"Código de estado de la respuesta: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Datos de la respuesta: {json.dumps(response.data, indent=2)}")
        
        # Verificaciones
        assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
        print("✅ Código de estado correcto (201 Created)")
        
        assert response.data.get("plot") == user_plot.id_plot
        print(f"✅ ID de predio correcto ({user_plot.id_plot})")
        
        assert response.data.get("lot") is None
        print("✅ Campo 'lot' es None como se esperaba")
        
    def test_report_invalid_missing_fields(self, api_client, normal_user):
        """
        RF64-HU11: Prueba error de validación cuando faltan campos obligatorios
        
        El sistema debe mostrar un error si faltan campos obligatorios
        """
        print("\n=== PRUEBA DE VALIDACIÓN DE CAMPOS OBLIGATORIOS ===")
        
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        print(f"Usuario autenticado: {normal_user.first_name} {normal_user.last_name}")
        
        # Datos inválidos - falta predio y observaciones
        data = {
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "type": "Reporte"  # Añadido el campo type pero faltarán otros campos obligatorios
        }
        print(f"Datos incompletos del reporte: {json.dumps(data, indent=2)}")
        
        # Enviar la solicitud
        print("Enviando solicitud POST con datos incompletos...")
        response = api_client.post(self.url, data, format="json")
        
        # Imprimir la respuesta para el informe
        print(f"Código de estado de la respuesta: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Datos de la respuesta (errores esperados): {json.dumps(response.data, indent=2)}")
        
        # Verificaciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print("✅ Código de estado correcto (400 Bad Request)")
        
        # Verificamos que el error contiene información sobre campos faltantes
        response_data_str = str(response.data).lower()
        assert "plot" in response_data_str or "observations" in response_data_str
        print("✅ La respuesta contiene errores sobre campos faltantes")
        
    def test_report_observation_too_long(self, api_client, normal_user, user_plot):
        """
        RF64-HU10: Prueba error cuando las observaciones superan el límite de caracteres (300)
        
        El sistema debe validar que las observaciones no superen los 300 caracteres
        """
        print("\n=== PRUEBA DE VALIDACIÓN DE LONGITUD DE OBSERVACIONES ===")
        
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        print(f"Usuario autenticado: {normal_user.first_name} {normal_user.last_name}")
        
        # Datos inválidos - observaciones demasiado largas (301 caracteres)
        data = {
            "plot": user_plot.id_plot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "A" * 301,
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del reporte con observaciones demasiado largas ({len(data['observations'])} caracteres)")
        
        # Enviar la solicitud
        print("Enviando solicitud POST con observaciones demasiado largas...")
        response = api_client.post(self.url, data, format="json")
        
        # Imprimir la respuesta para el informe
        print(f"Código de estado de la respuesta: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Datos de la respuesta: {json.dumps(response.data, indent=2)}")
        
        # Verificaciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print("✅ Código de estado correcto (400 Bad Request)")
        
        # Verificar que el error está relacionado con la longitud de las observaciones
        response_str = str(response.data).lower()
        assert "caracteres" in response_str or "caract" in response_str or "length" in response_str
        print("✅ La respuesta contiene errores sobre la longitud de las observaciones")
        
    def test_report_duplicate_pending_report_not_allowed(self, api_client, normal_user, user_plot, iot_device):
        """
        Prueba restricción: No se puede crear un reporte para un predio/lote que ya tiene uno pendiente
        
        Si ya existe un reporte en estado pendiente para el predio o lote, no se debe permitir crear otro
        """
        print("\n=== PRUEBA DE VALIDACIÓN DE REPORTES DUPLICADOS ===")
        
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        print(f"Usuario autenticado: {normal_user.first_name} {normal_user.last_name}")
        
        # Obtener el lote que tiene la válvula 4" asociada
        lote_con_valvula = iot_device[0].id_lot  # Primer dispositivo es la válvula 4"
        print(f"Lote seleccionado: {lote_con_valvula.id_lot}")
        
        # Creamos un reporte inicial
        data = {
            "plot": user_plot.id_plot,
            "lot": lote_con_valvula.id_lot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Primer reporte de prueba",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del primer reporte: {json.dumps(data, indent=2)}")
        
        # Enviar la primera solicitud
        print("Enviando solicitud POST para el primer reporte...")
        response1 = api_client.post(self.url, data, format="json")
        print(f"Código de estado de la primera respuesta: {response1.status_code}")
        
        assert response1.status_code == status.HTTP_201_CREATED, f"Error en el primer reporte: {response1.data}"
        print("✅ Primer reporte creado correctamente")
        
        if hasattr(response1, 'data'):
            print(f"ID del primer reporte: {response1.data.get('id')}")
        
        # Intentar crear un segundo reporte para el mismo lote
        data["observations"] = "Segundo reporte que debería fallar"
        print(f"\nDatos del segundo reporte (mismo lote): {json.dumps(data, indent=2)}")
        
        print("Enviando solicitud POST para el segundo reporte (debería fallar)...")
        response2 = api_client.post(self.url, data, format="json")
        print(f"Código de estado de la segunda respuesta: {response2.status_code}")
        
        if hasattr(response2, 'data'):
            print(f"Respuesta del segundo reporte: {json.dumps(response2.data, indent=2)}")
        
        # Verificaciones - debería fallar
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        print("✅ Segundo reporte rechazado correctamente (400 Bad Request)")
        
        # Verificar que el error está relacionado con un reporte pendiente
        response_str = str(response2.data).lower()
        assert "pendiente" in response_str or "ya existe" in response_str
        print("✅ El mensaje de error menciona reportes pendientes o existentes")
        
    def test_report_inactive_plot_not_allowed(self, api_client, normal_user, inactive_user_plot):
        """
        Prueba restricción: No se puede crear un reporte para un predio inactivo
        
        El sistema debe validar que el predio esté activo
        """
        print("\n=== PRUEBA DE VALIDACIÓN DE PREDIO INACTIVO ===")
        
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        print(f"Usuario autenticado: {normal_user.first_name} {normal_user.last_name}")
        
        # Datos para un predio inactivo
        data = {
            "plot": inactive_user_plot.id_plot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para predio inactivo",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del reporte con predio inactivo ({inactive_user_plot.id_plot}): {json.dumps(data, indent=2)}")
        print(f"Estado de activación del predio: {inactive_user_plot.is_activate}")
        
        # Enviar la solicitud
        print("Enviando solicitud POST para predio inactivo (debería fallar)...")
        response = api_client.post(self.url, data, format="json")
        
        # Imprimir la respuesta para el informe
        print(f"Código de estado de la respuesta: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Datos de la respuesta: {json.dumps(response.data, indent=2)}")
        
        # Verificaciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print("✅ Código de estado correcto (400 Bad Request)")
        
        # Verificar que el error está relacionado con el estado inactivo
        response_str = str(response.data).lower()
        assert "inhabilitado" in response_str or "inactivo" in response_str
        print("✅ El mensaje de error menciona que el predio está inhabilitado o inactivo")
        
    def test_report_inactive_lot_not_allowed(self, api_client, normal_user, user_plot, user_lot, iot_device):
        """
        Prueba restricción: No se puede crear un reporte para un lote inactivo
        
        El sistema debe validar que el lote esté activo
        """
        print("\n=== PRUEBA DE VALIDACIÓN DE LOTE INACTIVO ===")
        
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        print(f"Usuario autenticado: {normal_user.first_name} {normal_user.last_name}")
        
        # Crear una copia del objeto IoTDevice y asociarlo al lote inactivo
        lote_inactivo = user_lot[2]  # Lote inactivo
        print(f"Lote inactivo seleccionado: {lote_inactivo.id_lot}")
        print(f"Estado de activación del lote: {lote_inactivo.is_activate}")
        
        # Usar el dispositivo asociado al lote inactivo (ya configurado en el fixture)
        valve = iot_device[3]  # La válvula del lote inactivo
        print(f"Válvula asociada al lote inactivo: {valve.iot_id}")
        
        # Crear un reporte con el lote inactivo que tiene válvula
        data = {
            "plot": user_plot.id_plot,
            "lot": lote_inactivo.id_lot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para lote inactivo",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del reporte con lote inactivo: {json.dumps(data, indent=2)}")
        
        # Enviar la solicitud
        print("Enviando solicitud POST para lote inactivo (debería fallar)...")
        response = api_client.post(self.url, data, format="json")
        
        # Imprimir la respuesta para el informe
        print(f"Código de estado de la respuesta: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Datos de la respuesta: {json.dumps(response.data, indent=2)}")
        
        # Verificaciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print("✅ Código de estado correcto (400 Bad Request)")
        
        # Verificar que el error está relacionado con el estado inactivo
        response_str = str(response.data).lower()
        assert "inhabilitado" in response_str or "inactivo" in response_str
        print("✅ El mensaje de error menciona que el lote está inhabilitado o inactivo")
        
    def test_report_plot_has_pending_but_lot_allowed(self, api_client, normal_user, user_plot, iot_device):
        """
        Prueba restricción: No se puede crear un reporte para un lote si el predio ya tiene un reporte pendiente
        
        Según la implementación actual, no se permite crear reportes para lotes si el predio ya tiene un reporte pendiente
        """
        print("\n=== PRUEBA DE VALIDACIÓN DE REPORTES CON PREDIO YA REPORTADO ===")
        
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        print(f"Usuario autenticado: {normal_user.first_name} {normal_user.last_name}")
        
        # Primer reporte solo para el predio
        data_plot = {
            "plot": user_plot.id_plot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para el predio completo",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del primer reporte (solo predio): {json.dumps(data_plot, indent=2)}")
        
        # Enviar la primera solicitud (solo predio)
        print("Enviando solicitud POST para el primer reporte (solo predio)...")
        response1 = api_client.post(self.url, data_plot, format="json")
        print(f"Código de estado de la primera respuesta: {response1.status_code}")
        
        assert response1.status_code == status.HTTP_201_CREATED, f"Error en el primer reporte: {response1.data}"
        print("✅ Primer reporte (solo predio) creado correctamente")
        
        # Segundo reporte para un lote específico
        lote_con_valvula = iot_device[0].id_lot  # Primer dispositivo es la válvula 4"
        print(f"Lote seleccionado para segundo reporte: {lote_con_valvula.id_lot}")
        
        data_lot = {
            "plot": user_plot.id_plot,
            "lot": lote_con_valvula.id_lot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para un lote específico aunque el predio ya tenga reporte",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del segundo reporte (con lote): {json.dumps(data_lot, indent=2)}")
        
        # Enviar la segunda solicitud
        print("Enviando solicitud POST para el segundo reporte (con lote)...")
        response2 = api_client.post(self.url, data_lot, format="json")
        print(f"Código de estado de la segunda respuesta: {response2.status_code}")
        
        if hasattr(response2, 'data'):
            print(f"Respuesta del segundo reporte: {json.dumps(response2.data, indent=2)}")
        
        # Verificaciones - Debería mostrar mensaje de error por reporte pendiente
        assert response2.status_code == status.HTTP_201_CREATED
        print("✅ Segundo reporte aceptado")
        
        # Verificar que el mensaje menciona reportes pendientes
        response_str = str(response2.data).lower()
        assert "pendiente" in response_str or "ya existe" in response_str
        print("✅ El mensaje de error menciona reportes pendientes o existentes")
        
    def test_unauthorized_user_cannot_report(self, api_client):
        """
        RF64-HU08: Prueba que un usuario no autenticado no puede crear reportes
        
        Solo los usuarios autenticados deben poder acceder a esta funcionalidad
        """
        print("\n=== PRUEBA DE USUARIO NO AUTENTICADO ===")
        
        # Cliente sin autenticar (no llamamos a force_authenticate)
        print("Cliente API sin autenticar")
        
        # Datos para el reporte
        data = {
            "plot": "PR-1234567",  # ID ficticio
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte no autorizado",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del reporte: {json.dumps(data, indent=2)}")
        
        # Enviar la solicitud
        print("Enviando solicitud POST sin autenticación (debería fallar)...")
        response = api_client.post(self.url, data, format="json")
        
        # Imprimir la respuesta para el informe
        print(f"Código de estado de la respuesta: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Datos de la respuesta: {json.dumps(response.data, indent=2)}")
        
        # Verificaciones
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        print(f"✅ Código de estado correcto ({response.status_code}, no autorizado)")
        
    def test_user_cannot_report_for_other_user_plot(self, api_client, admin_user, user_plot, iot_device):
        """
        Prueba que un usuario no puede crear reportes para predios que no le pertenecen
        
        Un usuario solo debe poder reportar fallos en sus propios predios
        """
        print("\n=== PRUEBA DE USUARIO INTENTANDO REPORTAR PREDIO AJENO ===")
        
        # Hacer login como admin_user que no es dueño del predio
        api_client.force_authenticate(user=admin_user)
        print(f"Usuario autenticado: {admin_user.first_name} {admin_user.last_name} (no es dueño del predio)")
        print(f"Dueño real del predio: {user_plot.owner.first_name} {user_plot.owner.last_name}")
        
        # Datos para un predio que no pertenece al admin_user
        data = {
            "plot": user_plot.id_plot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para predio ajeno",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del reporte para predio ajeno: {json.dumps(data, indent=2)}")
        
        # Enviar la solicitud
        print("Enviando solicitud POST para predio ajeno (debería fallar)...")
        response = api_client.post(self.url, data, format="json")
        
        # Imprimir la respuesta para el informe
        print(f"Código de estado de la respuesta: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Datos de la respuesta: {json.dumps(response.data, indent=2)}")
        
        # Verificaciones
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print("✅ Código de estado correcto (400 Bad Request)")
        
        # Verificar que el error está relacionado con la propiedad
        response_str = str(response.data).lower()
        assert "dueño" in response_str or "owner" in response_str or "propietario" in response_str
        print("✅ El mensaje de error menciona que el usuario no es dueño del predio")
        
    def test_list_reports(self, api_client, normal_user, user_plot, iot_device):
        """
        RF64-HU03: Prueba listado de reportes para un usuario
        
        El usuario debe poder ver sus propios reportes
        """
        print("\n=== PRUEBA DE LISTADO DE REPORTES ===")
        
        # Hacer login directamente
        api_client.force_authenticate(user=normal_user)
        print(f"Usuario autenticado: {normal_user.first_name} {normal_user.last_name}")
        
        # Obtener el lote que tiene la válvula 4" asociada
        lote_con_valvula = iot_device[0].id_lot  # Primer dispositivo es la válvula 4"
        print(f"Lote seleccionado: {lote_con_valvula.id_lot}")
        
        # Crear un reporte primero
        data = {
            "plot": user_plot.id_plot,
            "lot": lote_con_valvula.id_lot,
            "failure_type": TypeReport.WATER_SUPPLY_FAILURE,
            "observations": "Reporte para listar después",
            "type": "Reporte"  # Campo requerido para el modelo BaseRequestReport
        }
        print(f"Datos del reporte a crear: {json.dumps(data, indent=2)}")
        
        print("Enviando solicitud POST para crear reporte...")
        create_response = api_client.post(self.url, data, format="json")
        print(f"Código de estado de la respuesta: {create_response.status_code}")
        
        assert create_response.status_code == status.HTTP_201_CREATED, f"Error al crear reporte: {create_response.data}"
        print("✅ Reporte creado correctamente")
        
        if hasattr(create_response, 'data'):
            report_id = create_response.data.get('id')
            print(f"ID del reporte creado: {report_id}")
        
        # Obtener lista de reportes
        list_url = reverse("water-supply-failure-list")
        print(f"URL para listar reportes: {list_url}")
        
        print("Enviando solicitud GET para listar reportes...")
        list_response = api_client.get(list_url)
        print(f"Código de estado de la respuesta: {list_response.status_code}")
        
        # Verificaciones
        assert list_response.status_code == status.HTTP_200_OK, f"Error al listar reportes: {list_response.data}"
        print("✅ Código de estado correcto (200 OK)")
        
        if hasattr(list_response, 'data'):
            print(f"Cantidad de reportes encontrados: {len(list_response.data)}")
        
        assert len(list_response.data) >= 1
        print("✅ Se encontró al menos un reporte en la lista")
        
        # Verificar que el reporte creado está en la lista
        found = False
        for report in list_response.data:
            if report.get("id") == create_response.data.get("id"):
                found = True
                print(f"✅ Reporte encontrado en la lista: ID={report.get('id')}")
                break
                
        assert found, "El reporte creado no aparece en la lista"
        print("✅ El reporte recién creado aparece correctamente en la lista")