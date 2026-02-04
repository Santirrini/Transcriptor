"""
Módulo para la generación de minutas de reunión (Meeting Minutes).

Analiza la transcripción para extraer puntos clave, acuerdos y tareas pendientes
utilizando heurísticas basadas en palabras clave y estructura de texto.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class MeetingMinutes:
    """Estructura de una minuta de reunión."""
    date: str
    summary: str
    decisions: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)

class MinutesGenerator:
    """Generador heurístico de minutas de reunión."""

    # Palabras clave para identificación (ahora más inclusivas)
    DECISION_KEYWORDS = [
        "decid", "acord", "aprob", "resolu", "conclu",
        "acuerdo", "pacto", "determina"
    ]
    
    ACTION_KEYWORDS = [
        "tarea", "pendient", "encarg", "hacer", "enviar", "revisar",
        "preparar", "investigar", "organizar", "llamar", "contactar",
        "debe", "tiene que"
    ]

    def generate(self, text: str) -> MeetingMinutes:
        """
        Genera una minuta a partir del texto de transcripción.
        
        Args:
            text: Texto completo de la transcripción.
            
        Returns:
            Objeto MeetingMinutes con la información extraída.
        """
        if not text:
            return MeetingMinutes(date=self._get_current_date(), summary="No hay contenido para analizar.")

        # Limpiar texto
        text = text.strip()
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Extracción heurística
        summary = self._extract_summary(lines)
        decisions = self._extract_items(text, self.DECISION_KEYWORDS)
        action_items = self._extract_items(text, self.ACTION_KEYWORDS)
        topics = self._extract_topics(lines)

        return MeetingMinutes(
            date=self._get_current_date(),
            summary=summary,
            decisions=decisions,
            action_items=action_items,
            topics=topics
        )

    def _get_current_date(self) -> str:
        return datetime.now().strftime("%d/%m/%Y")

    def _extract_summary(self, lines: List[str]) -> str:
        """Extrae un resumen aproximado (primeras oraciones significativas)."""
        if not lines:
            return ""
        
        # Tomar los primeros 3 párrafos o líneas significativas
        summary_content = " ".join(lines[:3])
        if len(summary_content) > 300:
            summary_content = summary_content[:297] + "..."
            
        return summary_content

    def _extract_items(self, text: str, keywords: List[str]) -> List[str]:
        """Extrae oraciones que contienen palabras clave específicas."""
        items = []
        # Dividir por oraciones usando expresión regular simple
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if any(key in sentence.lower() for key in keywords):
                if len(sentence) > 5 and len(sentence) < 200:
                    # Evitar duplicados exactos
                    if sentence not in items:
                        items.append(sentence)
        
        return items[:10]  # Limitar a los 10 más relevantes

    def _extract_topics(self, lines: List[str]) -> List[str]:
        """Intenta identificar temas principales basados en oraciones cortas o enfáticas."""
        topics = []
        for line in lines:
            # Si una línea es corta y termina en vocal o letra (no punto), podría ser un tema/título
            if 5 < len(line) < 50 and not line.endswith(('.', '!', '?')):
                topics.append(line)
        
        return topics[:5]

    def format_as_text(self, minutes: MeetingMinutes) -> str:
        """Formatea la minuta como una cadena de texto legible."""
        output = [
            f"📋 MINUTA DE REUNIÓN - {minutes.date}",
            "=" * 40,
            "\n📝 RESUMEN EJECUTIVO",
            minutes.summary,
            "\n🤝 ACUERDOS Y DECISIONES",
        ]
        
        if minutes.decisions:
            for d in minutes.decisions:
                output.append(f"  • {d}")
        else:
            output.append("  (No se identificaron acuerdos específicos)")

        output.append("\n✅ TAREAS PENDIENTES (ACTION ITEMS)")
        if minutes.action_items:
            for a in minutes.action_items:
                output.append(f"  • {a}")
        else:
            output.append("  (No se identificaron tareas específicas)")

        output.append("\n📌 TEMAS TRATADOS")
        if minutes.topics:
            for t in minutes.topics:
                output.append(f"  • {t}")
        else:
            output.append("  (Ver transcripción completa para más detalle)")

        return "\n".join(output)
