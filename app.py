import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# CONFIGURAÇÃO OTIMIZADA PARA O RENDER
uri = os.environ.get('DATABASE_URL', 'sqlite:///projeto.db')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

# Adiciona o SSL via código caso você esqueça no painel
if uri and "sslmode" not in uri and "localhost" not in uri:
    separator = "&" if "?" in uri else "?"
    uri += f"{separator}sslmode=require"

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Restante do seu código (Classe Cliente, Rotas, etc...) continua igual