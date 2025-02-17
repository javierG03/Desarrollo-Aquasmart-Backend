import React from 'react'
import InputItem from '../../components/InputItem'

const Login = () => {
    return (
        <div className="w-full h-full min-h-screen bg-[#DCF2F1] flex flex-col items-center justify-center gap-10">
            <div className='flex justify-center'>
                <img src="../../../public/img/logo.png" alt="Logo" className='w-full lg:w-[50%]'/>
            </div>
            <div className="w-[70%] lg:w-[30%] bg-white p-6  border-[#003F88] shadow-lg rounded-lg mx-auto flex flex-col justify-center items-center">
                <h1 className='text-4xl font-bold pb-8 text-center'>INICIO DE SESIÓN</h1>
                <form action="" className='flex flex-col items-center w-full'>
                    <InputItem
                        id="cedula"
                        labelName="Cédula de Ciudadanía"
                        placeholder="Ingresa tu Cédula de Ciudadanía"
                        type="number"
                    />
                    <InputItem
                        id="password"
                        labelName="Contraseña"
                        placeholder="Ingresa tu contraseña"
                        type="password"
                    />
                    <div className="flex flex-col items-center gap-2">
                        <a href="" className='font-semibold text-sm hover:underline'>OLVIDÉ MI CONTRASEÑA</a>
                        <a href="" className='font-semibold text-sm hover:underline'>SOY USUARIO NUEVO</a>
                    </div>
                    <button type="submit" className="w-[60%] sm:w-[35%] mt-4 bg-[#365486] text-white py-2 px-2 rounded-lg hover:bg-[#344663] hover:scale-105 transition-all duration-300 ease-in-out">
                        INICIAR SESIÓN
                    </button>
                </form>
            </div>

        </div>



    )
}

export default Login