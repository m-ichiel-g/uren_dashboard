# Gebruik een slanke Python-basis
FROM python:3.10-slim

# Zorg dat pip up-to-date is
RUN pip install --upgrade pip

# Zet werkdirectory
WORKDIR /app

# Kopieer je code en dependencies
COPY . /app

# Installeer afhankelijkheden
RUN pip install -r requirements.txt

# Streamlit port is standaard 8501
EXPOSE 8501

# Start Streamlit bij container-run
CMD sh -c "streamlit run uren_dashboard.py --server.port=\$PORT --server.address=0.0.0.0"
