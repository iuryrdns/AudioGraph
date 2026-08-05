import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

sns.set_theme(style="whitegrid")
plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'figure.titlesize': 14,
    'axes.edgecolor': '#cccccc',
    'grid.color': '#e6e6e6'
})

def gerar_relatorio_visual(caminho_csv: str):
    df = pd.read_csv(caminho_csv)
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    COR_LINHA = '#2b5c8f'
    COR_DISPERSAO = '#4c72b0'
    COR_REGRESSAO = '#2f4f4f'

    fig1, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    sim_cols = ['minimum_similarity', 'average_similarity', 'maximum_similarity']
    df_sim = df[sim_cols].melt(var_name='Tipo', value_name='Similaridade')
    sns.boxplot(
        data=df_sim, 
        x='Tipo', 
        y='Similaridade', 
        ax=axes[0], 
        palette=['#8faadc', '#4b75b3', '#1f4e78']
    )
    axes[0].set_title('Distribuição de Similaridades (Mínima, Média e Máxima)')
    axes[0].set_xticklabels(['Mínima', 'Média', 'Máxima'])
    axes[0].set_xlabel('')
    
    sns.scatterplot(
        data=df, 
        x='average_similarity', 
        y='diversity', 
        hue='sequence_len', 
        palette='mako',
        size='graph_coverage', 
        sizes=(30, 200),
        ax=axes[1]
    )
    axes[1].set_title('Trade-off: Similaridade Média vs. Diversidade')
    axes[1].set_xlabel('Similaridade Média')
    axes[1].set_ylabel('Diversidade')
    axes[1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    fig1.savefig('data/charts/1_qualidade_e_diversidade.png', dpi=300)
    
    fig2, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    sns.lineplot(
        data=df, 
        x='sequence_len', 
        y='average_cost', 
        marker='o', 
        color=COR_LINHA, 
        ax=axes[0]
    )
    axes[0].set_title('Custo Médio do Caminho vs. Tamanho da Sequência')
    axes[0].set_xlabel('Tamanho da Sequência')
    axes[0].set_ylabel('Custo Médio no Grafo')
    
    sns.regplot(
        data=df, 
        x='graph_density', 
        y='average_cost', 
        ax=axes[1], 
        scatter_kws={'color': COR_DISPERSAO, 'alpha': 0.6}, 
        line_kws={'color': COR_REGRESSAO}
    )
    axes[1].set_title('Impacto da Densidade do Grafo no Custo Médio')
    axes[1].set_xlabel('Densidade do Grafo (graph_density)')
    axes[1].set_ylabel('Custo Médio')

    plt.tight_layout()
    fig2.savefig('data/charts/2_custo_e_grafo.png', dpi=300)

    fig3, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    if 'threshold' in df.columns and 'top_k' in df.columns:
        pivot_sim = df.pivot_table(index='threshold', columns='top_k', values='average_similarity', aggfunc='mean')
        sns.heatmap(pivot_sim, annot=True, fmt=".3f", cmap="Blues", ax=axes[0], cbar_kws={'label': 'Similaridade'})
        axes[0].set_title('Similaridade Média por Threshold e Top-K')
        axes[0].set_xlabel('Top-K')
        axes[0].set_ylabel('Threshold')

        pivot_cov = df.pivot_table(index='threshold', columns='top_k', values='graph_coverage', aggfunc='mean')
        sns.heatmap(pivot_cov, annot=True, fmt=".3f", cmap="GnBu", ax=axes[1], cbar_kws={'label': 'Cobertura'})
        axes[1].set_title('Cobertura do Grafo por Threshold e Top-K')
        axes[1].set_xlabel('Top-K')
        axes[1].set_ylabel('Threshold')

    plt.tight_layout()
    fig3.savefig('data/charts/3_hiperparametros.png', dpi=300)


    fig4, axes = plt.subplots(1, 2, figsize=(14, 5))

    sns.boxplot(
        data=df, 
        x='sequence_len', 
        y='recommendation_time_seconds', 
        ax=axes[0], 
        palette="light:slategrey"
    )
    axes[0].set_title('Tempo de Recomendação vs. Tamanho da Sequência')
    axes[0].set_xlabel('Tamanho da Sequência')
    axes[0].set_ylabel('Tempo de Recomendação (s)')
    
    sns.scatterplot(
        data=df, 
        x='average_degree', 
        y='build_time_seconds', 
        hue='graph_density', 
        palette='crest',
        ax=axes[1]
    )
    axes[1].set_title('Tempo de Construção do Grafo vs. Grau Médio')
    axes[1].set_xlabel('Grau Médio (average_degree)')
    axes[1].set_ylabel('Tempo de Construção do Grafo (s)')

    plt.tight_layout()
    fig4.savefig('data/charts/4_desempenho_tempos.png', dpi=300)

    plt.show()

gerar_relatorio_visual("data/relatorio.csv")