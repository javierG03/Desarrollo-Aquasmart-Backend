import React from "react";
import { render, screen } from "@testing-library/react";
import InputItem from "../components/InputItem";

describe("InputItem Component", () => {
  test("renderiza correctamente con las props dadas", () => {
    render(
      <InputItem
        labelName="Nombre"
        id="nombre"
        placeholder="Ingrese su nombre"
        type="text"
      />
    );

    // Verifica que el label se renderiza correctamente
    expect(screen.getByLabelText("Nombre")).toBeInTheDocument();

    // Verifica que el input se renderiza correctamente con el placeholder
    const inputElement = screen.getByPlaceholderText("Ingrese su nombre");
    expect(inputElement).toBeInTheDocument();
    expect(inputElement).toHaveAttribute("type", "text");
  });

  test("permite escribir en el input", () => {
    render(
      <InputItem id="test-input" type="text" placeholder="Escriba aquí" />
    );

    const inputElement = screen.getByPlaceholderText("Escriba aquí");

    expect(inputElement).toBeInTheDocument();
  });
});
