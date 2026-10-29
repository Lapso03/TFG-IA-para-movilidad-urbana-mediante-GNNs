# IA para movilidad urbana mediante GNNs

Trabajo de Fin de Grado del Grado en Ingeniería Informática (Universidad de Burgos).

- **Autor:** Sergio Buil Laliena
- **Tutor:** Bruno Baruque Zanon

## Descripción

Aplicación web que permite consultar, en lenguaje natural, el estado y la predicción del tráfico en ciudades españolas. Un modelo de lenguaje responde a las preguntas apoyándose en un servidor basado en el *Model Context Protocol* (MCP), que expone herramientas de consulta y de predicción construidas sobre modelos LSTM y redes neuronales de grafos (GNN).

## Estado

Proyecto en desarrollo (fase inicial). El seguimiento se hace con *issues* de GitHub, uno por sprint de dos semanas.

## Estructura

```
.
├── doc/                  Documentación (LaTeX)
│   ├── memoria.tex       Memoria del TFG
│   ├── anexos.tex        Anexos
│   ├── tex/              Capítulos y apéndices
│   ├── img/              Imágenes
│   ├── bibliografia*.bib Referencias
│   └── lecturas/         Resúmenes de los artículos leídos
└── src/                  Código fuente
```

## Cómo compilar la documentación

Requiere una distribución de LaTeX (TeX Live o MiKTeX) con `latexmk`.

```bash
cd doc
latexmk -pdf memoria.tex
latexmk -pdf anexos.tex
```

En Visual Studio Code, con la extensión *LaTeX Workshop*, basta con abrir `doc/memoria.tex` o `doc/anexos.tex` y pulsar `Ctrl+Alt+B`.