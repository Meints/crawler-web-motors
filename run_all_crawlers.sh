#!/bin/bash

# Script para executar todos os crawlers
echo "Iniciando execução de todos os crawlers"

# Verificar se deve executar em paralelo
if [ "$PARALLEL_EXECUTION" = "true" ]; then
    echo "Executando crawlers em paralelo"
    
    # Executar crawlers em paralelo usando &
    cd /app/aleks && python crawler.py &
    cd /app/Cadu && python Icarros.py &
    cd /app/Pedro && python SemiNovos.py &
    cd /app/Thiago/crawler && python WebMotors.py &
    
    # Aguardar todos os processos terminarem
    wait
else
    echo "Executando crawlers sequencialmente"
    
    # Executar crawlers em sequência
    echo "Iniciando crawler OLX (Aleks)"
    cd /app/aleks && python crawler.py
    
    echo "Iniciando crawler iCarros (Cadu)"
    cd /app/Cadu && python Icarros.py
    
    echo "Iniciando crawler SemiNovos (Pedro)"
    cd /app/Pedro && python SemiNovos.py
    
    echo "Iniciando crawler WebMotors (Thiago)"
    cd /app/Thiago/crawler && python WebMotors.py
fi

echo "Todos os crawlers foram executados"
