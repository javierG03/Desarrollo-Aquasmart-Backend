import { TextEncoder, TextDecoder } from 'util';

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;


import React from 'react';
import { render, screen } from '@testing-library/react';
import NavBar from '../components/NavBar';
import { MemoryRouter } from 'react-router-dom'; // Necesario para manejar las rutas en las pruebas

describe('NavBar', () => {
  test('renders the Navbar correctly', () => {
    render(
      <MemoryRouter>
        <NavBar />
      </MemoryRouter>
    );

    // Verificamos si el logo está presente
    const logo = screen.getByAltText('Logo');
    expect(logo).toBeInTheDocument();

    // Verificamos que los enlaces estén presentes
    const links = [
      'Perfil',
      'Control IoT',
      'Gestión de Registros',
      'Facturación',
      'Historial de consumo',
      'Predicciones',
      'Permisos'
    ];

    links.forEach(linkText => {
      const linkElement = screen.getByText(linkText);
      expect(linkElement).toBeInTheDocument();
    });
  });

  test('all links are functional', () => {
    render(
      <MemoryRouter>
        <NavBar />
      </MemoryRouter>
    );

    // Verificar que cada link tenga un "href"
    const links = screen.getAllByRole('link');
    links.forEach(link => {
      expect(link).toHaveAttribute('href');
    });
  });
});
