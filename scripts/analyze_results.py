import ast
import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"

COLOR_PRIMARY = "#4A5568"
COLOR_SECONDARY = "#8EA0B5"
COLOR_ACCENT = "#2B6CB0"

pasta_saida = "data/charts"
os.makedirs(pasta_saida, exist_ok=True)

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
      "Arquivo 'relatorio.csv' não foi encontrado na pasta atual nem na pasta"
      " 'data/'."
  )

df = pd.read_csv(csv_path)
print(f"Carregados {len(df)} registros de '{csv_path}'.\n")

print("--- RESUMO DAS MÉTRICAS ---")
colunas_metricas = [
    "average_similarity",
    "diversity",
    "average_cost",
    "graph_coverage",
    "graph_density",
    "recommendation_time_seconds",
    "build_time_seconds",
]
colunas_presentes = [c for c in colunas_metricas if c in df.columns]
print(df[colunas_presentes].describe().T[["mean", "std", "min", "max"]])

if {"minimum_similarity", "average_similarity", "maximum_similarity"}.issubset(
    df.columns
):
  fig, ax = plt.subplots(figsize=(10, 5))

  df_sim = df[
      ["minimum_similarity", "average_similarity", "maximum_similarity"]
  ].melt(var_name="Métrica", value_name="Valor")
  df_sim["Métrica"] = df_sim["Métrica"].map({
      "minimum_similarity": "Mínima",
      "average_similarity": "Média",
      "maximum_similarity": "Máxima",
  })

  sns.boxplot(
      data=df_sim,
      x="Métrica",
      y="Valor",
      palette=[COLOR_SECONDARY, COLOR_PRIMARY, COLOR_ACCENT],
      ax=ax,
  )

  ax.set_title(
      "Distribuição dos Níveis de Similaridade da Recomendação",
      fontsize=12,
      fontweight="bold",
  )
  ax.set_xlabel("Métrica de Similaridade")
  ax.set_ylabel("Similaridade (0 a 1)")

  plt.tight_layout()
  fig.subplots_adjust(top=0.90)
  plt.savefig(
      os.path.join(pasta_saida, "distribuicao_similaridades.png"),
      dpi=300,
      bbox_inches="tight",
  )
  plt.close()


if "recommendation_time_seconds" in df.columns:
  fig, ax = plt.subplots(figsize=(9, 5))

  tempo_ms = df["recommendation_time_seconds"] * 1000

  sns.histplot(
      tempo_ms,
      kde=True,
      color=COLOR_ACCENT,
      ax=ax,
      bins=15,
      edgecolor="white",
      linewidth=1,
  )

  ax.set_title(
      "Distribuição do Tempo de Recomendação por Execução",
      fontsize=12,
      fontweight="bold",
  )
  ax.set_xlabel("Tempo de Processamento (ms)")
  ax.set_ylabel("Frequência")

  media_tempo = tempo_ms.mean()
  ax.axvline(
      media_tempo,
      color="red",
      linestyle="--",
      linewidth=1.5,
      label=f"Média: {media_tempo:.2f} ms",
  )
  ax.legend()

  plt.tight_layout()
  fig.subplots_adjust(top=0.90)
  plt.savefig(
      os.path.join(pasta_saida, "tempo_recomendacao_distribuicao.png"),
      dpi=300,
      bbox_inches="tight",
  )
  plt.close()


if "recommendation_types" in df.columns:
  tipos_contagem = {}
  for item in df["recommendation_types"].dropna():
    try:
      d_type = (
          ast.literal_eval(item) if isinstance(item, str) else item
      )
      for k, v in d_type.items():
        tipos_contagem[k] = tipos_contagem.get(k, 0) + v
    except (ValueError, SyntaxError):
      continue

  if tipos_contagem:
    df_tipos = (
        pd.DataFrame(
            list(tipos_contagem.items()), columns=["Tipo de Caminho", "Total"]
        )
        .sort_values(by="Total", ascending=False)
        .head(10)
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(
        data=df_tipos,
        y="Tipo de Caminho",
        x="Total",
        color=COLOR_PRIMARY,
        ax=ax,
    )

    ax.set_title(
        "Frequência Total dos Tipos de Caminho (Recomendações)",
        fontsize=12,
        fontweight="bold",
  )
    ax.set_xlabel("Contagem Total de Ocorrências")
    ax.set_ylabel("Tipo de Ligação no Grafo")

    plt.tight_layout()
    fig.subplots_adjust(top=0.90)
    plt.savefig(
        os.path.join(pasta_saida, "frequencia_tipos_recomendacao.png"),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()


colunas_num = df.select_dtypes(include=["float64", "int64"]).dropna(
    axis=1, how="all"
)

cols_ignorar = [
    "random_seed",
    "seed_index",
    "requested_count",
    "top_k",
    "threshold",
]
cols_corr = [c for c in colunas_num.columns if c not in cols_ignorar]

if len(cols_corr) > 1:
  fig, ax = plt.subplots(figsize=(10, 7))

  cmap_frio = sns.diverging_palette(220, 20, as_cmap=True)
  sns.heatmap(
      df[cols_corr].corr(),
      annot=True,
      cmap=cmap_frio,
      fmt=".2f",
      ax=ax,
      cbar_kws={"label": "Coeficiente de Correlação"},
  )

  ax.set_title("Matriz de Correlação das Métricas", fontsize=12, fontweight="bold")

  plt.tight_layout()
  fig.subplots_adjust(top=0.92)
  plt.savefig(
      os.path.join(pasta_saida, "correlacao.png"), dpi=300, bbox_inches="tight"
  )
  plt.close()


metricas_chave = [
    c
    for c in [
        "average_similarity",
        "diversity",
        "graph_coverage",
        "recommendation_time_seconds",
    ]
    if c in df.columns
]

if len(metricas_chave) > 1:
  pair_grid = sns.pairplot(
      df[metricas_chave],
      diag_kind="kde",
      plot_kws={"alpha": 0.6, "s": 35, "color": COLOR_ACCENT},
      diag_kws={"color": COLOR_PRIMARY, "fill": True, "alpha": 0.4},
  )

  pair_grid.fig.suptitle(
      "Matriz de Dispersão das Métricas Chave do Sistema",
      y=1.02,
      fontsize=14,
      fontweight="bold",
  )

  pair_grid.savefig(
      os.path.join(pasta_saida, "matriz_dispersao_pairplot.png"),
      dpi=300,
      bbox_inches="tight",
  )
  plt.close()

print(f"\nPronto! Os gráficos otimizados foram salvos em '{pasta_saida}/'.")