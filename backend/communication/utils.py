import hashlib
import uuid

def generate_unique_id(model,prefix):
        """Genera un ID único para el modelo dado, asegurando que no exista en la base de datos"""
        while True:
            unique_value = str(uuid.uuid4())
            hash_obj = hashlib.md5(unique_value.encode())
            hash_int = int(hash_obj.hexdigest(), 16)
            numeric_part = str(hash_int)[:6] # toma los primeros 6 digitos del hash
            generated_id = prefix + numeric_part# Genera el ID único con el prefijo
            #Verifica si el ID Ya existe en la base de datos            
            if not model.objects.filter(id=generated_id).exists():
                # Si no existe, devuelve el ID generado
                return int(generated_id)
