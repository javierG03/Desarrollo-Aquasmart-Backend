# Desarrollo-Aquasmart
Repositorio de desarrollo del sistema de gestion de distritos de riego acorde a la documentacion realizada el semestre pasado
## Backend

#### Clonar repositorio SSH.
`git clone git@github.com:SebiceC/Desarrollo-Aquasmart.git `

#### Clonar repositorio HTTPS.
`git clone https://github.com/SebiceC/Desarrollo-Aquasmart.git `

#### Entrar a la carpeta del proyecto
`cd Desarrollo-Aquasmart`

#### Crear entorno virtual
`python -m venv venv`

#### Instalar las dependencias del archivo requirements.txt
`pip install -r requirements.txt`

#### Ejecutar las migraciones
`python manage.py migrate`

#### Crear SuperUsuario
`python manage.py createsuperuser`

#### Crear archivo .env
dentro del el archivo .env se crea sa sigiente variable
`SECRET_KEY ='palabar secreta`
se puede dejar esa palabra o cambiar si lo desea.

#### Lanzamiento del servidor
`python manage.py runserver`
