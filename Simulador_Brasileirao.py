# URL da CBF:
# https://www.cbf.com.br/api/proxy?path=/jogos/tabela-detalhada/campeonato/12606
# URL da Gazeta Esportiva
# https://footstats.gazetaesportiva.com/campeonatos/brasileiro-serie-a-2025/partidas/

import streamlit as st
import requests
from random import random
import pandas as pd
import matplotlib.pyplot as plt
import Utilidades
from pprint import pprint

# ---------- Configurações iniciais ----------
RODADA_FINAL = 38
ANO          = '2025'

class Times():
  def __init__(self):
    self.times = dict()
  # __init__
  
  def pega_um_time(self, nome):
    self.times[Utilidades.LimpaTexto(nome)] = {
        'partidas_mandante' : 0,
        'vitorias_mandante' : 0,
        'empates_mandante'  : 0,
        'derrotas_mandante' : 0,
        'partidas_visitante': 0,
        'vitorias_visitante': 0,
        'empates_visitante' : 0,
        'derrotas_visitante': 0,
        'pontos': 0.0,
    }
  # pega_um_time

  def pega_times(self):
    """Pega a lista de times a partir da rodada 1."""
    # url = 'https://www.cbf.com.br/api/proxy?path=/jogos/tabela-detalhada/campeonato/12606'
    url = f'https://footstats.gazetaesportiva.com/campeonatos/brasileiro-serie-a-{ANO}/partidas/'
    resp = requests.get(url)
    resp.raise_for_status()
    self.todos_jogos = resp.json()
    
    rodada_1 = [jogo for jogo in self.todos_jogos if jogo['rodada'] == 1]

    for jogo in rodada_1:
      try: # o cara muda o nome do campo !!!
        self.pega_um_time(jogo['equipeMandante']['nome'])
        self.pega_um_time(jogo['equipeVisitante']['nome'])
      except:
        self.pega_um_time(jogo['equipe_mandante']['nome'])
        self.pega_um_time(jogo['equipe_visitante']['nome'])
      # fim_try
    # next
    return
  # pega_times

  def executar_simulacao(self, rodada_inicial=1, nr_simulacoes=10000, st_progress_callback=None):

    # Preenche times e obtém jogos pendentes
    jogos_faltantes = self.preenche_times_e_jogos(rodada_inicial)

    # Calcula probabilidades para cada jogo pendente
    for i, jogo in enumerate(jogos_faltantes.jogos):
      mand, vis, _, _, _ = jogo
      prob_man, prob_vis, prob_emp = probabilidade_resultado(
        self.times[mand]['vitorias_mandante'], self.times[mand]['empates_mandante'], self.times[mand]['derrotas_mandante'],
        self.times[vis]['vitorias_visitante'], self.times[vis]['empates_visitante'], self.times[vis]['derrotas_visitante']
      )
      jogos_faltantes.jogos[i][2] = prob_man
      jogos_faltantes.jogos[i][3] = prob_man + prob_vis
      jogos_faltantes.jogos[i][4] = prob_man + prob_vis + prob_emp
    # next

    # Simulações Monte Carlo
    resultados = {um_time: [0] * 20 for um_time in self.times}

    for simulacao in range(nr_simulacoes):
      # barra de progresso opcional
      if st_progress_callback and simulacao % max(1, nr_simulacoes // 100) == 0:
          st_progress_callback(simulacao / nr_simulacoes)
      # endif

      dic_pontuacao_simulada = {um_time: self.times[um_time]['pontos'] for um_time in self.times}

      for jogo in jogos_faltantes.jogos:
        mandante, visitante, prob_man, prob_vis, prob_emp = jogo
        sorteio = random()
        if sorteio < prob_man:
          dic_pontuacao_simulada[mandante] += 3.01
        elif sorteio < prob_vis:
          dic_pontuacao_simulada[visitante] += 3.01
        else:
          dic_pontuacao_simulada[mandante] += 1
          dic_pontuacao_simulada[visitante] += 1
        # endif
      # next
      colocacao = sorted(dic_pontuacao_simulada.items(), key=lambda um_time: um_time[1], reverse=True)
      for lugar, um_time in enumerate(colocacao):
        resultados[um_time[0]][lugar] += 1
      # next
    # next

    # Retorna dataframe com probabilidades
    df = pd.DataFrame(resultados)
    df.index = df.index + 1
    df_prob = 100 * df / nr_simulacoes
    sorted_columns = df_prob.iloc[0].sort_values(ascending=False).index
    df_prob = df_prob[sorted_columns]
    df_prob = df_prob.applymap(lambda x: round(x))
    return df_prob
  # executar_simulacao

  def preenche_times_e_jogos(self, rodada_inicial=1):
    jogos_faltantes = JogosNaoRealizados()

    for jogo in self.todos_jogos:
      if int(jogo['rodada']) < rodada_inicial: continue
      try: # o cara muda o nome dos campos !!!
        mandante  = Utilidades.LimpaTexto(jogo['equipeMandante']['nome'])
        visitante = Utilidades.LimpaTexto(jogo['equipeVisitante']['nome'])
      except:
        mandante  = Utilidades.LimpaTexto(jogo['equipe_mandante']['nome'])
        visitante = Utilidades.LimpaTexto(jogo['equipe_visitante']['nome'])
      # fim_try

      if jogo['partidaEncerrada'] == False:
        jogos_faltantes.jogos.append([mandante, visitante, 0.0, 0.0, 0.0])
      else:
        self.times[mandante]['partidas_mandante']   += 1
        self.times[visitante]['partidas_visitante'] += 1

        if int(jogo['placar']['golsMandante']) == int(jogo['placar']['golsVisitante']):
          self.times[mandante]['empates_mandante'] += 1
          self.times[mandante]['pontos'] += 1
          self.times[visitante]['empates_visitante'] += 1
          self.times[visitante]['pontos'] += 1
        elif int(jogo['placar']['golsMandante']) > int(jogo['placar']['golsVisitante']):
          self.times[mandante]['vitorias_mandante'] += 1
          self.times[mandante]['pontos'] += 3.01
          self.times[visitante]['derrotas_visitante'] += 1
        else:
          self.times[mandante]['derrotas_mandante'] += 1
          self.times[visitante]['vitorias_visitante'] += 1
          self.times[visitante]['pontos'] += 3.01
        # endif
      # endif
    # next
    return jogos_faltantes
  # preenche_times_e_jogos

# fim classe Times

class JogosNaoRealizados:
  def __init__(self):
    self.jogos = []  # cada item: [mandante, visitante, prob_man, prob_vis_cumul, prob_total_cumul]
  # __init__
#fim classe JogosNaoRealizados

def probabilidade_resultado(vitorias_mandante, empates_mandante, derrotas_mandante,
                            vitorias_visitante, empates_visitante, derrotas_visitante):
    vetor_mandante = [3] * vitorias_mandante + [1] * empates_mandante + [0] * derrotas_mandante
    vetor_visitante = [0] * derrotas_visitante + [1] * empates_visitante + [3] * vitorias_visitante

    nr_comparacoes = min(len(vetor_mandante), len(vetor_visitante))
    if nr_comparacoes == 0:
        # sem histórico suficiente: retornar probabilidades uniformes
        return 0.33, 0.33, 0.34

    prob_mandante = prob_visitante = prob_empate = 0
    for jogo in range(nr_comparacoes):
        if vetor_mandante[jogo] > vetor_visitante[jogo]:
            prob_mandante += 1
        elif vetor_mandante[jogo] < vetor_visitante[jogo]:
            prob_visitante += 1
        else:
            prob_empate += 1

    return prob_mandante / nr_comparacoes, prob_visitante / nr_comparacoes, prob_empate / nr_comparacoes
# probabilidade_resultado

# ---------- Streamlit App ----------

def main():
    def update_progress(p):
      progresso_bar.progress(min(1.0, max(0.0, p)))
    # update_progress

    st.set_page_config(page_title="Simulador do Brasileirão", layout="wide")
    st.title("⚽ Simulador do Brasileirão")
    st.title('base: Gazeta Esportiva')

    with st.sidebar:
      st.header("Configurações")
      # ano = st.number_input("Ano", min_value=2010, max_value=2030, value=2025, step=1)
      rodada_inicial = st.number_input("Rodada inicial (para recalcular a partir de)", min_value=1, max_value=38, value=1, step=1)
      nr_simulacoes = st.number_input("Número de simulações", min_value=100, max_value=20000, value=10000, step=100)
      run = st.button("Executar simulação")
    # end_with

    placeholder_status = st.empty()
    progresso_bar = st.progress(0)

    if run:
      try:
        placeholder_status.info("Buscando e processando dados... (isso pode demorar alguns segundos)")

        times = Times()
        times.pega_times()
        df_prob = times.executar_simulacao(rodada_inicial, nr_simulacoes, st_progress_callback=update_progress)

        placeholder_status.success("Simulação concluída com sucesso!")

        # Mostrar tabela resumida
        st.subheader("Probabilidades de posição (1 a 20)")
        st.dataframe(df_prob)

        # Mostrar gráficos - 20 gráficos, dois por linha
        colors = ['#29681E', '#339523', '#3AC426', '#3FF527',
                  '#27B4F5', '#2A91C4', '#286F94', '#224E68',
                  '#69411A', '#965A1F', '#C47523', '#F59127',
                  '#AC9B25', '#C42126', '#DCC727', '#F5DD27',
                  '#AD261F', '#C52722', '#DD2724', '#F52727'
                 ]
        st.subheader("Gráficos de distribuição por time")
        cols = st.columns(2)
        count = 0
        for time_name in df_prob.columns:
          fig, ax = plt.subplots(figsize=(8, 8))
          # ax.plot(df_prob.index, df_prob[time_name], marker='o')          
          ax.bar(df_prob.index, df_prob[time_name], color=colors)
          ax.set_title(time_name, fontsize=16)
          ax.set_xlabel('Posição')
          ax.set_ylabel('Probabilidade (%)')
          ax.set_xticks(range(1, 21))
          ax.grid(True, linestyle='--', alpha=0.4)
          plt.ylim(0, 100)

          cols[count % 2].pyplot(fig)
          plt.close(fig)
          count += 1
        # next

        # Estatísticas rápidas
        st.subheader("Resumo: probabilidades-chave")
        resumo = pd.DataFrame(index=df_prob.columns)
        resumo['Campeonato (posição 1)'] = df_prob.loc[1]
        resumo['Top4 (soma posições 1-4)'] = df_prob.loc[1:4].sum()
        resumo['Z4 (soma posições 17-20)'] = df_prob.loc[17:20].sum()
        st.table(resumo.sort_values('Campeonato (posição 1)', ascending=False))

      except requests.HTTPError as e:
        placeholder_status.error(f"Erro nas requisições HTTP: {e}")
      except Exception as e:
        placeholder_status.error(f"Erro inesperado: {e}")
      # fim_try
    # endif
# fim main


if __name__ == '__main__':
  main()
  # times = Times()
  # times.pega_times()
  # df_prob = times.executar_simulacao(1, 1000, None)