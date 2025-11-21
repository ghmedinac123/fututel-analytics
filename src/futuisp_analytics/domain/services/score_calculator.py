# domain/services/score_calculator.py
"""Servicio de dominio para cálculo de scores."""
from typing import Dict


class ScoreCalculator:
    """Calcula scores de comportamiento de pago."""
    
    # Pesos por período
    PESO_OPTIMO = 100      # Día 1-10
    PESO_ACEPTABLE = 75    # Día 11 hasta corte
    PESO_CRITICO = 40      # Día corte hasta 30
    PESO_PENDIENTE = 0     # Sin pagar o día 31+
    
    @staticmethod
    def calcular_score(
        total_facturas: int,
        facturas_optimas: int,
        facturas_aceptables: int,
        facturas_criticas: int,
        facturas_pendientes: int,
    ) -> float:
        """
        Calcula score ponderado (0-100).
        
        Fórmula única:
        Score = (
            OPTIMO × 100 +
            ACEPTABLE × 75 +
            CRITICO × 40 +
            PENDIENTE × 0
        ) / total_facturas
        
        Args:
            total_facturas: Total de facturas del cliente
            facturas_optimas: Pagadas en día 1-10
            facturas_aceptables: Pagadas día 11 hasta corte
            facturas_criticas: Pagadas después de corte hasta día 30
            facturas_pendientes: Sin pagar o después del día 31
            
        Returns:
            Score entre 0.0 y 100.0
        """
        if total_facturas == 0:
            return 0.0
        
        puntos = (
            facturas_optimas * ScoreCalculator.PESO_OPTIMO +
            facturas_aceptables * ScoreCalculator.PESO_ACEPTABLE +
            facturas_criticas * ScoreCalculator.PESO_CRITICO +
            facturas_pendientes * ScoreCalculator.PESO_PENDIENTE
        )
        
        return round(puntos / total_facturas, 2)
    
    @staticmethod
    def calcular_nivel_riesgo(score: float) -> str:
        """
        Determina nivel de riesgo según score.
        
        Args:
            score: Score calculado (0-100)
            
        Returns:
            Nivel de riesgo: BAJO, MEDIO, ALTO, CRITICO
        """
        if score >= 90:
            return "BAJO"
        elif score >= 70:
            return "MEDIO"
        elif score >= 50:
            return "ALTO"
        else:
            return "CRITICO"
    
    @staticmethod
    def calcular_porcentaje_puntualidad(
        total_facturas: int,
        facturas_optimas: int
    ) -> float:
        """
        Calcula porcentaje de facturas pagadas a tiempo.
        
        Args:
            total_facturas: Total de facturas
            facturas_optimas: Facturas pagadas en día 1-10
            
        Returns:
            Porcentaje de puntualidad (0-100)
        """
        if total_facturas == 0:
            return 0.0
        return round((facturas_optimas / total_facturas) * 100, 2)