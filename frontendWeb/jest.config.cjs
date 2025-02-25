module.exports = {
  testEnvironment: "jsdom",
  moduleNameMapper: {
    "^.+\\.svg$": "jest-svg-transformer",
    "^.+\\.(css|less|scss)$": "identity-obj-proxy",
    "\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$":
      "<rootDir>/__mocks__/fileMock.cjs",
  },
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],

  // Configuración de reportes
  reporters: [
    "default",
    [
      "jest-html-reporter",
      {
        outputPath: "test-report.html",
        pageTitle: "Reporte de Pruebas Jest",
        includeFailureMsg: true,
        includeConsoleLog: true,
      },
    ],
    [
      "jest-stare",
      {
        resultDir: "jest-stare",
        reportTitle: "Jest Test Report",
        additionalResultsProcessors: ["jest-junit"],
      },
    ],
  ],
};
