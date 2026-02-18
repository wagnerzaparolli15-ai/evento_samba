@echo off
echo [PROCESSO DE ORGANIZACAO DO EVENTO]

:: 1. Criar estrutura de pastas do Flask
if not exist "templates" mkdir "templates"
if not exist "static" mkdir "static"
if not exist "database" mkdir "database"

echo Pastas verificadas...

:: 2. Mover arquivos para as pastas corretas (caso estejam fora)
if exist "index.html" move "index.html" "templates\"
if exist "admin.html" move "admin.html" "templates\"

:: 3. Instrucao para a logo
echo.
echo [AVISO] Certifique-se de que sua logo (logo-evento.png) esta na pasta 'static'.
echo.

:: 4. Executar o servidor Python
echo Iniciando o Servidor Flask...
python app.py

pause