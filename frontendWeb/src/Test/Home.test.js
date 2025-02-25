import React from "react";
import { render, screen } from "@testing-library/react";
import Home from "../Home.jsx";
import NavBar from "../components/NavBar";

// Mock de NavBar para evitar errores si su implementación no es relevante para esta prueba
jest.mock("../components/NavBar", () => () => (
  <div data-testid="navbar-mock">Mocked NavBar</div>
));

test("renders Home component with NavBar", () => {
  render(<Home />);

  // Verifica que el componente Home se renderiza
  expect(screen.getByTestId("navbar-mock")).toBeInTheDocument();
});
