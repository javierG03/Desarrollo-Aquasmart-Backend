from .models import CustomUser,Otp
from rest_framework.exceptions import NotFound
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import ValidationError
def validate_user(document):
    """
    Valida la existencia de un usuario a partir de su documento de identidad.

    Esta función busca un usuario en la base de datos utilizando el documento de identidad proporcionado.
    Si el usuario existe, lo devuelve; de lo contrario, lanza una excepción indicando que no se encontró.

    Parámetros:
    - `document` (str): Número de documento de identidad del usuario.

    Retorno:
    - `CustomUser`: Instancia del usuario si existe en la base de datos.

    Excepciones:
    - `NotFound`: Si no se encuentra un usuario con el documento proporcionado.
    """
    try:
        user = CustomUser.objects.get(document=document)
        return user
    except CustomUser.DoesNotExist:
        raise NotFound({"detail": "Usuario no encontrado con este documento."})
def validate_otp(user, is_validated=False, otp=None):
    """
    Valida si existe un OTP según el estado de validación.
    
    - `user`: Usuario al que pertenece el OTP.
    - `is_validated`: `True` para buscar OTPs ya validados, `False` para buscar OTPs no usados.
    - `otp`: (Opcional) Código OTP a verificar.
    
    Retorna el objeto OTP si existe, de lo contrario lanza un error.
    """
    try:
        filters = {"user": user, "is_validated": is_validated}
        if otp is not None:
            filters["otp"] = otp  # Filtrar por OTP si se proporciona
        
        return Otp.objects.get(**filters)
    
    except ObjectDoesNotExist:
        message = (
            "No hay un OTP validado para este usuario."
            if is_validated else "OTP inválido o ya ha sido utilizado."
        )
        raise ValidationError({"detail": message})