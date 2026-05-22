# LitFlow Scripts

## Windows Development Startup

From the project root, run:

```bat
start-litflow.bat
```

or double-click `start-litflow.bat` in File Explorer.

The script opens separate terminal windows for:

- Backend: `http://127.0.0.1:8000/docs`
- Frontend: `http://localhost:5173`

To stop the development servers, close the terminal windows or run:

```bat
stop-litflow.bat
```

`stop-litflow.bat` only prints safe stop instructions and does not kill ports automatically.
