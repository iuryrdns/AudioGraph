import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", palette="gray")
plt.style.use("grayscale")

candidatos_csv = [
    os.path.join("data", "relatorio.csv"),
    "relatorio.csv",
]

csv_path = None
for caminho in candidatos_csv:
    if os.path.exists(caminho):
        csv_path = caminho
        break

if not csv_path:
    raise FileNotFoundError(
        "Arquivo 'relatorio.csv' não foi encontrado na pasta atual nem na pasta 'data/'."
    )

df = pd.read_csv(csv_path)
print(f"Carregados {len(df)} registros de '{csv_path}'.\n")

print("--- RESUMO DAS MÉTRICAS ---")
colunas_metricas = [
    "average_similarity",
    "diversity",
    "average_cost",
    "recommendation_time_seconds",
]
colunas_presentes = [c for c in colunas_metricas if c in df.columns]
print(df[colunas_presentes].describe().T[["mean", "std", "min", "max"]])

pasta_saida = "data/charts"
os.makedirs(pasta_saida, exist_ok=True)
sns.set_theme(style="whitegrid", palette="Greys")

# --- GRÁFICO 1: Distribuição de Similaridade e Diversidade (Boxplot) ---
if "average_similarity" in df.columns and "diversity" in df.columns:
    plt.figure(figsize=(8, 5))
    df_melt = df.melt(
        value_vars=["average_similarity", "diversity"],
        var_name="Métrica",
        value_name="Valor",
    )
    sns.boxplot(x="Métrica", y="Valor", data=df_melt)
    plt.title("Distribuição de Similaridade e Diversidade")
    plt.savefig(os.path.join(pasta_saida, "similaridade_vs_diversidade.png"))
    plt.close()

# --- GRÁFICO 2: Tempo de Recomendação ---
if "recommendation_time_seconds" in df.columns:
    plt.figure(figsize=(8, 4))
    plt.plot(
        df.index,
        df["recommendation_time_seconds"] * 1000,
        marker="o",
        color="green",
    )
    plt.title("Tempo de Recomendação por Execução (ms)")
    plt.xlabel("Execução")
    plt.ylabel("Tempo (ms)")
    plt.savefig(os.path.join(pasta_saida, "tempo_recomendacao.png"))
    plt.close()

# --- GRÁFICO 3: Matriz de Correlação ---
colunas_num = df.select_dtypes(include=["float64", "int64"]).dropna(
    axis=1, how="all"
)
if len(colunas_num.columns) > 1:
    plt.figure(figsize=(11, 8))
    sns.heatmap(colunas_num.corr(), annot=True, cmap="coolwarm", fmt=".2f")
    plt.title("Matriz de Correlação")
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, "correlacao.png"))
    plt.close()

# --- GRÁFICO 4: Matriz de Dispersão Par a Par (Pairplot) ---
if len(colunas_presentes) > 1:
    pair_grid = sns.pairplot(
        df[colunas_presentes],
        diag_kind="kde",
        plot_kws={
            "alpha": 0.65,
            "s": 30,
            "color": "#444444",
        },
        diag_kws={
            "color": "#888888",
            "edgecolor": "#444444",
        },
    )

    pair_grid.fig.suptitle(
        "Matriz de Dispersão Par a Par das Métricas",
        y=1.02,
        fontsize=14,
        fontweight="bold",
    )

    pair_grid.savefig(
        os.path.join(
            pasta_saida,
            "matriz_dispersao_pairplot.png",
        ),
        dpi=300,
        bbox_inches="tight",
    )

    plt.close()

print(f"\nPronto! Os gráficos foram salvos na pasta '{pasta_saida}/'.")