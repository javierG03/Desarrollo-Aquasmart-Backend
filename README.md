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

#### Crear las migraciones
`python manage.py makemigrations`

#### Ejecutar las migraciones
`python manage.py migrate`

#### Crear SuperUsuario
`python manage.py createsuperuser`

#### Lanzamiento del servidor
`python manage.py runserver`
