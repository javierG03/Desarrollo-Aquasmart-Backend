import pytest
from rest_framework.test import APIClient
from django.utils import timezone
from dateutil import parser
from django.contrib.auth import get_user_model
from caudal.models import FlowMeasurementLote
from plots_lots.models import Plot, Lot, SoilType
from iot.models import IoTDevice, DeviceType
from django.urls import reverse

User = get_user_model()

@pytest.mark.django_db
class TestLotConsumptionHistory:
    @pytest.fixture
    def create_authorized_user(self, db):
        """Create an authorized user with necessary permissions"""
        user = User.objects.create_user(
            document="123456789012", 
            first_name="Authorized", 
            last_name="User", 
            email="authorized@example.com", 
            phone="1234567890", 
            password="SecurePass123@",
            is_active=True,
            is_registered=True
        )
        print(f"🔐 Authorized User Created:")
        print(f"   📋 Document: {user.document}")
        print(f"   👤 Name: {user.get_full_name()}")
        print(f"   📧 Email: {user.email}")
        return user

    @pytest.fixture
    def create_plot_and_lot(self, create_authorized_user):
        """Create a plot and lot for the authorized user"""
        # Create soil type
        soil_type = SoilType.objects.create(name="Arcilloso")
        print(f"🌱 Soil Type Created: {soil_type.name}")
        
        # Create plot
        plot = Plot.objects.create(
            plot_name="Test Plot", 
            owner=create_authorized_user, 
            latitud=1.0, 
            longitud=1.0, 
            plot_extension=100.0
        )
        print(f"🏞️ Plot Created:")
        print(f"   🏷️ Name: {plot.plot_name}")
        print(f"   👤 Owner: {plot.owner.get_full_name()}")
        print(f"   📍 Location: {plot.latitud}, {plot.longitud}")
        
        # Create lot
        lot = Lot.objects.create(
            plot=plot, 
            soil_type=soil_type,
            crop_type="Maíz",
            crop_variety="Híbrido"
        )
        print(f"🌾 Lot Created:")
        print(f"   🆔 Lot ID: {lot.id_lot}")
        print(f"   🌱 Crop: {lot.crop_type} - {lot.crop_variety}")
        print(f"   🏞️ Plot: {lot.plot.plot_name}")
        
        return plot, lot

    @pytest.fixture
    def create_device_and_measurements(self, create_plot_and_lot):
        """Create IoT device and flow measurements for the lot"""
        plot, lot = create_plot_and_lot
        
        # Create device type
        device_type = DeviceType.objects.create(name="Sensor de Flujo")
        print(f"🌐 Device Type Created: {device_type.name}")
        
        # Create IoT device
        device = IoTDevice.objects.create(
            name="Test Flow Sensor", 
            id_lot=lot, 
            device_type=device_type
        )
        print(f"📡 IoT Device Created:")
        print(f"   🏷️ Name: {device.name}")
        print(f"   🆔 Device ID: {device.iot_id}")
        print(f"   🌾 Assigned to Lot: {device.id_lot.id_lot}")
        
        # Create flow measurements for the last 6 months
        now = timezone.now()
        measurements = [
            FlowMeasurementLote(
                lot=lot, 
                device=device, 
                timestamp=now - timezone.timedelta(days=30), 
                flow_rate=15.5  # Litros por segundo (L/s)
            ),
            FlowMeasurementLote(
                lot=lot, 
                device=device, 
                timestamp=now - timezone.timedelta(days=60), 
                flow_rate=14.8  # Litros por segundo (L/s)
            ),
            FlowMeasurementLote(
                lot=lot, 
                device=device, 
                timestamp=now - timezone.timedelta(days=90), 
                flow_rate=16.2  # Litros por segundo (L/s)
            )
        ]
        created_measurements = FlowMeasurementLote.objects.bulk_create(measurements)
        
        print(f"📊 Flow Measurements Created:")
        for measurement in created_measurements:
            print(f"   📅 Timestamp: {measurement.timestamp}")
            print(f"   💧 Flow Rate: {measurement.flow_rate} m³/s")
        
        return device, created_measurements

    @pytest.fixture
    def authenticated_client(self, create_authorized_user):
        """Create an authenticated API client"""
        client = APIClient()
        client.force_authenticate(user=create_authorized_user)
        print(f"🔓 Authenticated Client Created for user: {create_authorized_user.get_full_name()}")
        return client

    def test_lot_consumption_history_retrieval(self, authenticated_client, create_plot_and_lot, create_device_and_measurements):
        """
        Test that an authorized user can retrieve consumption history for their lot
        RF46-HU03: Visualization of lots
        """
        plot, lot = create_plot_and_lot
        
        print("\n🔍 Test: Lot Consumption History Retrieval")
        print(f"📌 Testing retrieval for Lot ID: {lot.id_lot}")
        
        # Construct URL for lot consumption history
        url = f"/api/caudal/flow-measurements/lote/{lot.id_lot}"
        print(f"🌐 Request URL: {url}")
        
        # Retrieve consumption history
        response = authenticated_client.get(url)
        
        print(f"📡 Response Status: {response.status_code}")
        
        # Assertions
        assert response.status_code == 200, f"Failed to retrieve lot consumption history. Response: {response.json()}"
        
        measurements = response.json()
        print(f"📊 Total Measurements Retrieved: {len(measurements)}")
        
        assert len(measurements) > 0, "No measurements found for the lot"
        
        # Verify each measurement has required fields
        for i, measurement in enumerate(measurements, 1):
            print(f"\n🔢 Measurement {i}:")
            print(f"   🆔 Lot: {measurement.get('lot', 'N/A')}")
            print(f"   📡 Device: {measurement.get('device', 'N/A')}")
            print(f"   📅 Timestamp: {measurement.get('timestamp', 'N/A')}")
            print(f"   💧 Flow Rate: {measurement.get('flow_rate', 'N/A')} L/s")
            
            assert 'lot' in measurement, "Measurement missing lot information"
            assert 'device' in measurement, "Measurement missing device information"
            assert 'timestamp' in measurement, "Measurement missing timestamp"
            assert 'flow_rate' in measurement, "Measurement missing flow rate"

    def test_unauthorized_user_cannot_access_other_lot_history(self, create_plot_and_lot):
        """
        Test that a user cannot access consumption history of a lot they do not own
        RF46-HU03: Lot visualization restrictions
        """
        # Create another user
        other_user = User.objects.create_user(
            document="987654321098", 
            first_name="Other", 
            last_name="User", 
            email="other@example.com", 
            phone="0987654321", 
            password="SecurePass123@",
            is_active=True,
            is_registered=True
        )
        
        print("\n🔍 Test: Unauthorized User Access")
        print(f"🚫 Unauthorized User: {other_user.get_full_name()}")
        
        # Create client for the other user
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        
        # Get the lot from the first plot
        plot, lot = create_plot_and_lot
        
        print(f"🏞️ Target Lot: {lot.id_lot}")
        print(f"🏞️ Lot Owner: {plot.owner.get_full_name()}")
        
        # Try to access lot consumption history
        url = f"/api/caudal/flow-measurements/lote/{lot.id_lot}"
        print(f"🌐 Request URL: {url}")
        
        response = other_client.get(url)
        
        print(f"📡 Response Status: {response.status_code}")
        print(f"📝 Response Details: {response.json()}")
        
        # Assert forbidden access
        assert response.status_code == 403, "Unauthorized user should not access lot consumption history"

    def test_lot_consumption_history_time_interval(self, authenticated_client, create_plot_and_lot, create_device_and_measurements):
        """
        Test consumption history retrieval with time interval
        RF46-HU04: Time interval selection
        """
        plot, lot = create_plot_and_lot
        
        print("\n🔍 Test: Lot Consumption History Time Interval")
        
        # Calculate time intervals
        now = timezone.now()
        start_date = (now - timezone.timedelta(days=120)).isoformat()
        end_date = now.isoformat()
        
        print(f"📅 Time Interval:")
        print(f"   🟢 Start Date: {start_date}")
        print(f"   🔴 End Date: {end_date}")
        
        # Construct URL with time interval parameters
        url = f"/api/caudal/flow-measurements/lote/{lot.id_lot}?start_date={start_date}&end_date={end_date}"
        print(f"🌐 Request URL: {url}")
        
        # Retrieve consumption history
        response = authenticated_client.get(url)
        
        print(f"📡 Response Status: {response.status_code}")
        
        # Assertions
        assert response.status_code == 200, f"Failed to retrieve lot consumption history with time interval. Response: {response.json()}"
        
        measurements = response.json()
        print(f"📊 Total Measurements Retrieved: {len(measurements)}")
        
        assert len(measurements) > 0, "No measurements found for the specified time interval"
        
        # Verify measurements are within the specified time range
        for i, measurement in enumerate(measurements, 1):
            timestamp = parser.parse(measurement['timestamp'])
            
            print(f"\n🔢 Measurement {i}:")
            print(f"   📅 Timestamp: {timestamp.isoformat()}")
            print(f"   💧 Flow Rate: {measurement['flow_rate']} m³/s")
            
            assert start_date <= timestamp.isoformat() <= end_date, "Measurement outside specified time interval"

    def test_lot_consumption_history_no_data(self, authenticated_client, create_plot_and_lot):
        """
        Test handling of lot with no consumption history
        RF46-HU05: Alert for lack of consumption data
        """
        plot, lot = create_plot_and_lot
        
        print("\n🔍 Test: Lot Consumption History No Data")
        
        # Calculate time intervals for a period with no data
        now = timezone.now()
        start_date = (now - timezone.timedelta(days=365)).isoformat()
        end_date = (now - timezone.timedelta(days=300)).isoformat()
        
        print(f"📅 Time Interval:")
        print(f"   🟢 Start Date: {start_date}")
        print(f"   🔴 End Date: {end_date}")
        
        # Construct URL with time interval parameters
        url = f"/api/caudal/flow-measurements/lote/{lot.id_lot}?start_date={start_date}&end_date={end_date}"
        print(f"🌐 Request URL: {url}")
        
        # Retrieve consumption history
        response = authenticated_client.get(url)
        
        print(f"📡 Response Status: {response.status_code}")
        
        # Assertions
        assert response.status_code == 200, f"Failed to handle lot with no consumption data. Response: {response.json()}"
        
        measurements = response.json()
        print(f"📊 Total Measurements Retrieved: {len(measurements)}")
        
        assert len(measurements) == 0, "Expected no measurements for the specified time interval"

    def test_lot_owner_can_access_consumption_history(self, create_plot_and_lot, create_device_and_measurements):
        """
        Test that the lot owner can access their own lot's consumption history
        RF46-HU03: Lot visualization for owner
        """
        plot, lot = create_plot_and_lot
        
        print("\n🔍 Test: Lot Owner Consumption History Access")
        print(f"🏞️ Lot Details:")
        print(f"   🆔 Lot ID: {lot.id_lot}")
        print(f"   👤 Lot Owner: {plot.owner.get_full_name()}")
        
        # Create client for the lot owner (who created the plot)
        owner_client = APIClient()
        owner_client.force_authenticate(user=plot.owner)
        
        # Construct URL for lot consumption history
        url = f"/api/caudal/flow-measurements/lote/{lot.id_lot}"
        print(f"🌐 Request URL: {url}")
        
        # Retrieve consumption history
        response = owner_client.get(url)
        
        print(f"📡 Response Status: {response.status_code}")
        
        # Assertions
        assert response.status_code == 200, f"Lot owner failed to access consumption history. Response: {response.json()}"
        
        measurements = response.json()
        print(f"📊 Total Measurements Retrieved: {len(measurements)}")
        
        assert len(measurements) > 0, "No measurements found for the lot owned by the user"
        
        # Verify each measurement is for the correct lot
        for i, measurement in enumerate(measurements, 1):
            print(f"\n🔢 Measurement {i}:")
            print(f"   🆔 Lot ID: {measurement['lot']}")
            print(f"   💧 Flow Rate: {measurement['flow_rate']} m³/s")
            print(f"   📅 Timestamp: {measurement['timestamp']}")
            
            assert str(measurement['lot']) == str(lot.id_lot), "Measurement does not belong to the correct lot"