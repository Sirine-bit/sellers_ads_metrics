"""
Charts - Générateur de graphiques pour le dashboard
"""
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any
import pandas as pd


class ChartGenerator:
    """Génère tous les graphiques du dashboard"""
    
    # Palette de couleurs
    COLORS = {
        'converty': '#10b981',      # Vert
        'concurrent': '#ef4444',    # Rouge
        'active': '#22c55e',        # Vert clair
        'inactive': '#6b7280',      # Gris
        'neutral': '#3b82f6'        # Bleu
    }
    
    def create_progress_gauge(self, progression: float, label: str = "Progression") -> go.Figure:
        """
        Jauge de progression circulaire
        
        Args:
            progression: Pourcentage (0-100)
            label: Libellé de la jauge
        """
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=progression,
            title={'text': label, 'font': {'size': 20}},
            delta={'reference': 100, 'increasing': {'color': self.COLORS['converty']}},
            gauge={
                'axis': {'range': [None, 100], 'ticksuffix': '%'},
                'bar': {'color': self.COLORS['converty']},
                'steps': [
                    {'range': [0, 50], 'color': "#fecaca"},
                    {'range': [50, 80], 'color': "#fed7aa"},
                    {'range': [80, 100], 'color': "#d1fae5"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 100
                }
            }
        ))
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=60, b=20))
        return fig
    
    def create_time_series(self, dates: List, values_dict: Dict[str, List]) -> go.Figure:
        """
        Graphique en ligne temporel
        
        Args:
            dates: Liste de dates
            values_dict: {'label': [values], ...}
        """
        fig = go.Figure()
        
        for label, values in values_dict.items():
            color = self.COLORS.get(label.lower(), self.COLORS['neutral'])
            fig.add_trace(go.Scatter(
                x=dates,
                y=values,
                mode='lines+markers',
                name=label,
                line=dict(color=color, width=3),
                marker=dict(size=8)
            ))
        
        fig.update_layout(
            title="Évolution temporelle",
            xaxis_title="Date",
            yaxis_title="Nombre",
            hovermode='x unified',
            template='plotly_white',
            height=400
        )
        
        return fig
    
    def create_area_chart(self, dates: List, values: List, label: str) -> go.Figure:
        """
        Graphique en aire (rempli)
        
        Args:
            dates: Liste de dates
            values: Liste de valeurs
            label: Nom de la série
        """
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=values,
            fill='tozeroy',
            name=label,
            line=dict(color=self.COLORS['converty'], width=2),
            fillcolor='rgba(16, 185, 129, 0.3)'
        ))
        
        fig.update_layout(
            title=f"{label} - Évolution cumulée",
            xaxis_title="Date",
            yaxis_title="Nombre cumulé",
            template='plotly_white',
            height=400
        )
        
        return fig
    
    def create_pie_chart(self, labels: List[str], values: List[int], title: str) -> go.Figure:
        """
        Graphique camembert
        
        Args:
            labels: Noms des catégories
            values: Valeurs
            title: Titre
        """
        colors = [self.COLORS['active'], self.COLORS['inactive']] if len(labels) == 2 else None
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,  # Donut chart
            marker=dict(colors=colors) if colors else None,
            textposition='inside',
            textinfo='label+percent'
        )])
        
        fig.update_layout(
            title=title,
            height=400,
            showlegend=True
        )
        
        return fig
    
    def create_bar_chart(self, labels: List[str], values: List[int], 
                        title: str, horizontal: bool = False) -> go.Figure:
        """
        Graphique en barres
        
        Args:
            labels: Noms des catégories
            values: Valeurs
            title: Titre
            horizontal: Barres horizontales si True
        """
        if horizontal:
            fig = go.Figure(go.Bar(
                x=values,
                y=labels,
                orientation='h',
                marker=dict(color=self.COLORS['neutral'])
            ))
            fig.update_layout(xaxis_title="Nombre", yaxis_title="")
        else:
            fig = go.Figure(go.Bar(
                x=labels,
                y=values,
                marker=dict(color=self.COLORS['neutral'])
            ))
            fig.update_layout(xaxis_title="", yaxis_title="Nombre")
        
        fig.update_layout(
            title=title,
            template='plotly_white',
            height=400
        )
        
        return fig
    
    def create_stacked_bar(self, categories: List[str], 
                          data_dict: Dict[str, List[int]], title: str) -> go.Figure:
        """
        Barres empilées (stacked)
        
        Args:
            categories: Catégories X
            data_dict: {'label': [values], ...}
            title: Titre
        """
        fig = go.Figure()
        
        colors = [self.COLORS['converty'], self.COLORS['concurrent']]
        for i, (label, values) in enumerate(data_dict.items()):
            fig.add_trace(go.Bar(
                name=label,
                x=categories,
                y=values,
                marker=dict(color=colors[i % len(colors)])
            ))
        
        fig.update_layout(
            barmode='stack',
            title=title,
            xaxis_title="",
            yaxis_title="Nombre",
            template='plotly_white',
            height=400
        )
        
        return fig
    
    def create_sunburst(self, data_df: pd.DataFrame, 
                       path: List[str], values: str, title: str) -> go.Figure:
        """
        Graphique sunburst (hiérarchique circulaire)
        
        Args:
            data_df: DataFrame avec les données
            path: Colonnes de hiérarchie ['Platform', 'Competitor']
            values: Colonne des valeurs
            title: Titre
        """
        fig = px.sunburst(
            data_df,
            path=path,
            values=values,
            title=title,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        
        fig.update_layout(height=500)
        return fig
    
    def create_histogram(self, values: List[int], bins: int, 
                        title: str, color: str = 'neutral') -> go.Figure:
        """
        Histogramme de distribution
        
        Args:
            values: Valeurs à distribuer
            bins: Nombre de bins
            title: Titre
            color: Clé couleur
        """
        fig = go.Figure(go.Histogram(
            x=values,
            nbinsx=bins,
            marker=dict(color=self.COLORS[color])
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Valeur",
            yaxis_title="Fréquence",
            template='plotly_white',
            height=400
        )
        
        return fig
